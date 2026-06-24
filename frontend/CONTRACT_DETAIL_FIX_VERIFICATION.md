# ContractDetailPage 串页问题修复验证

## 修复内容

修复了 `ContractDetailPage.tsx` 中全局 report 数据串页的问题。

### 问题根因
- `useReviewStore()` 的 `current` 是全局单例，不按 `contract_id` 或 `review_id` 隔离
- 页面直接使用 `const report = reportData as ReviewReport | null` 而不校验归属
- 当用户从合同 A（已完成审查）切换到合同 B 时，B 的页面会先显示 A 的报告数据

### 修复方案

#### 1. 合同切换时清空 review store（第 797-803 行）
```typescript
// Clear review store when contract changes to prevent cross-contamination
useEffect(() => {
  if (id) {
    clearReviewStore();
    void fetchContractDetail(id);
  }
}, [id, clearReviewStore, fetchContractDetail]);
```

**为什么**：确保每次进入新合同详情页时，全局 store 中的旧报告数据被清除。

#### 2. 严格校验 report 归属（第 812-821 行）
```typescript
const report = useMemo(() => {
  if (!reportData) return null;
  // Only use report if it matches the current activeReview or current contract
  if (activeReview && reportData.id !== activeReview.id) return null;
  if (selected && reportData.contract_id !== selected.id) return null;
  return reportData as ReviewReport;
}, [reportData, activeReview, selected]);
```

**为什么**：即使 store 中存在 report，也必须验证：
- `reportData.id === activeReview.id`（报告属于当前 review）
- `reportData.contract_id === selected.id`（报告属于当前合同）

只有通过验证的 report 才会被使用，否则返回 `null`。

#### 3. 报告切换时重置风险索引（第 829-831 行）
```typescript
// Reset activeRiskIndex when report changes to avoid stale index
useEffect(() => {
  setActiveRiskIndex(0);
}, [report]);
```

**为什么**：防止旧报告的 `activeRiskIndex` 索引落在新报告不存在的位置上（例如旧报告有 10 个风险，新报告只有 3 个）。

## 验证场景

### 场景 1：A → B 串页防护
1. 用户查看合同 A，触发审查，等待完成（此时 report 已加载到 store）
2. 用户点击返回工作台，进入合同 B 详情页
3. **预期**：页面不会显示 A 的风险队列和条款分析
4. **验证点**：
   - `clearReviewStore()` 在进入 B 时被调用
   - `report` 经过归属校验后返回 `null`（因为 store 已清空或 contract_id 不匹配）

### 场景 2：刷新页面
1. 用户在合同 B 详情页刷新浏览器
2. **预期**：不会看到其他合同的残留数据
3. **验证点**：刷新后 store 重新初始化，`reportData` 为 `null`

### 场景 3：并发审查
1. 用户在合同 A 详情页触发审查（review_1 running）
2. 切换到合同 B 详情页触发审查（review_2 running）
3. review_1 先完成，report_1 加载到 store
4. **预期**：合同 B 页面不会显示 report_1 的内容
5. **验证点**：
   - `report_1.contract_id !== selected.id`（B 的 id）
   - `report_1.id !== activeReview.id`（review_2 的 id）
   - report 校验返回 `null`

### 场景 4：风险索引越界防护
1. 用户在合同 A（10 个风险）查看第 8 个风险（activeRiskIndex = 7）
2. 切换到合同 B 详情页（3 个风险）
3. **预期**：显示第 1 个风险，不会因为索引 7 越界而崩溃
4. **验证点**：
   - `useEffect(() => setActiveRiskIndex(0), [report])` 在 report 变化时触发
   - `activeRiskIndex` 重置为 0

## 编译验证

```bash
✓ TypeScript 编译通过
✓ Vite build 通过（11.82s）
✓ 无类型错误
```

## 风险提示

### 当前修复已覆盖
- ✅ 合同切换时的串页
- ✅ report 归属校验
- ✅ 风险索引越界

### 仍需后续关注
1. **WebSocket 连接清理**：当前 `useEffect` cleanup 在组件卸载时会清理 WS，但快速切换时可能有短暂的旧连接残留（已有 cleanup 机制，风险较低）
2. **轮询定时器清理**：已有 `pollTimerRef` cleanup，但如果在轮询期间切换合同，理论上可能有一次旧请求返回（已在 `startPolling` 中做了 `clearTimeout`，风险可控）
3. **Race condition**：如果用户极快速度切换 A → B → A，可能有请求乱序返回，但因为有归属校验，错误的 report 会被过滤掉

### 建议后续增强（非紧急）
- 在 `fetchReport` 成功后，二次校验返回的 `report.contract_id` 是否仍然匹配当前页面
- 在 store 中记录 `lastFetchedContractId`，进一步隔离不同合同的数据流

## 测试清单

- [x] TypeScript 类型检查通过
- [x] Vite 构建通过
- [ ] 手动测试：A 合同完成 → 进入 B 合同详情页 → 确认不显示 A 的数据
- [ ] 手动测试：快速切换多个合同 → 确认每个页面只显示自己的报告
- [ ] 手动测试：刷新页面 → 确认无残留数据

## 总结

通过三处最小修改，确保了 `ContractDetailPage` 只展示当前合同最新 review 对应的报告，不会显示别的合同的旧报告。修复策略：
1. **入口清理**：合同切换时清空 store
2. **出口校验**：使用 report 前验证归属
3. **状态重置**：report 变化时重置依赖状态

修改范围小，侵入性低，符合"最小修改优先"原则。
