import { useEffect, useRef, useState } from 'react';
import { Button, message, Modal, Space, Tabs } from 'antd';
import {
  ArrowLeftOutlined,
  CheckOutlined,
  EditOutlined,
  EyeOutlined,
  FileTextOutlined,
  SaveOutlined,
} from '@ant-design/icons';

import { ContractEditor } from '../Editor';
import type { ReviewReport } from '../../api/types';
import { draftApi } from '../../api/client';

interface EditModeProps {
  contractId: string;
  contractTitle: string;
  originalContent: string;
  report: ReviewReport | null;
  activeRisk: ReviewReport['risks'][0] | null;
  onExit: () => void;
  onSave: (content: string) => void;
  onReReview: (content: string) => void;
  onApplySuggestion: (suggestion: string) => void;
}

export function EditMode({
  contractId,
  contractTitle,
  originalContent,
  report,
  activeRisk,
  onExit,
  onSave,
  onReReview,
  onApplySuggestion,
}: EditModeProps) {
  const [content, setContent] = useState(originalContent);
  const [baselineContent, setBaselineContent] = useState(originalContent);
  const [hasChanges, setHasChanges] = useState(false);
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit');
  const [messageApi, contextHolder] = message.useMessage();
  const [loading, setLoading] = useState(true);
  const lastLoadedDraftRef = useRef<string | null>(null);

  void report;

  useEffect(() => {
    const loadDraft = async () => {
      try {
        setLoading(true);
        const response = await draftApi.get(contractId);
        const serverContent = response.data?.content;

        if (serverContent) {
          setContent(serverContent);
          setBaselineContent(serverContent);
          setHasChanges(false);

          if (lastLoadedDraftRef.current !== serverContent) {
            messageApi.info('已加载服务端保存的草稿');
            lastLoadedDraftRef.current = serverContent;
          }
        } else {
          // 服务端没有草稿，使用 originalContent（可能包含建议插入）
          setContent(originalContent);
          setBaselineContent(originalContent);
          setHasChanges(false);
          lastLoadedDraftRef.current = null;
        }
      } catch (error) {
        console.error('Failed to load draft:', error);
        // Check if it's a network error (backend not running) vs other errors
        const axiosError = error as { code?: string; message?: string };
        if (axiosError.code === 'ERR_NETWORK' || axiosError.message?.includes('Network Error')) {
          // Backend not running - silently fall back to original content without warning
          console.warn('Backend not available, using original content');
        } else {
          // Other errors - show warning
          messageApi.warning('加载草稿失败，已回退到默认内容');
        }
        setContent(originalContent);
        setBaselineContent(originalContent);
        setHasChanges(false);
        lastLoadedDraftRef.current = null;
      } finally {
        setLoading(false);
      }
    };

    void loadDraft();
  }, [contractId, originalContent, messageApi]);

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    setHasChanges(newContent !== baselineContent);
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      await draftApi.save(contractId, content);
      setBaselineContent(content);
      setHasChanges(false);
      messageApi.success('草稿已保存到服务器');

      const draftKey = `contract-draft-${contractId}`;
      sessionStorage.setItem(draftKey, content);
      lastLoadedDraftRef.current = content;

      onSave(content);
    } catch (error) {
      console.error('Failed to save draft:', error);
      // Check if it's a network error (backend not running)
      const axiosError = error as { code?: string; message?: string };
      if (axiosError.code === 'ERR_NETWORK' || axiosError.message?.includes('Network Error')) {
        messageApi.error('后端服务未启动，无法保存到服务器。草稿已保存到本地浏览器。');
        // Still save to sessionStorage as fallback
        const draftKey = `contract-draft-${contractId}`;
        sessionStorage.setItem(draftKey, content);
        setBaselineContent(content);
        setHasChanges(false);
        onSave(content);
      } else {
        messageApi.error('保存草稿失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleReReview = () => {
    Modal.confirm({
      title: '确认基于草稿重新审查？',
      content: '将退出编辑模式，并使用当前草稿内容重新发起审查。',
      okText: '确认发起草稿审查',
      cancelText: '取消',
      onOk: () => {
        onReReview(content);
      },
    });
  };

  const handleApplySuggestion = () => {
    if (!activeRisk) {
      messageApi.warning('请先选择一个风险项');
      return;
    }

    const original = activeRisk.original_text;
    const suggestion = activeRisk.suggested_revision;

    if (original && content.includes(original)) {
      const newContent = content.replace(original, suggestion);
      setContent(newContent);
      setHasChanges(true);
      onApplySuggestion(suggestion);
      return;
    }

    const newContent = `${content}\n<h4>插入的建议内容</h4>\n<p>${suggestion}</p>`;
    setContent(newContent);
    setHasChanges(true);
    onApplySuggestion(suggestion);
    messageApi.info('未找到原文位置，已将建议内容插入到文档末尾');
  };

  const handleExit = () => {
    if (hasChanges) {
      Modal.confirm({
        title: '未保存的更改',
        content: '当前有未保存的更改，是否放弃更改并退出？',
        okText: '放弃更改',
        cancelText: '继续编辑',
        okButtonProps: { danger: true },
        onOk: onExit,
      });
      return;
    }

    onExit();
  };

  return (
    <div style={{ display: 'grid', gap: 18 }}>
      {contextHolder}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 18,
          padding: '16px 18px',
          borderRadius: 24,
          border: '1px solid rgba(24,36,47,0.1)',
          background: 'rgba(255,255,255,0.9)',
          boxShadow: 'var(--shadow-md)',
          backdropFilter: 'blur(18px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={handleExit}
            style={{ borderRadius: 999 }}
          >
            退出编辑
          </Button>
          <div>
            <strong style={{ display: 'block', fontSize: 14 }}>
              <EditOutlined style={{ marginRight: 6 }} />
              审查建议整理
            </strong>
            <span style={{ fontSize: 11, color: 'var(--ink-muted)' }}>
              {contractTitle} · 审查建议整理
            </span>
          </div>
        </div>

        <Space>
          {activeRisk && (
            <Button
              type="default"
              icon={<CheckOutlined />}
              onClick={handleApplySuggestion}
              style={{ borderRadius: 999 }}
            >
              插入当前建议
            </Button>
          )}
          <Button
            type="default"
            icon={<SaveOutlined />}
            onClick={handleSave}
            disabled={!hasChanges || loading}
            style={{ borderRadius: 999 }}
            title="保存到服务器"
          >
            保存草稿
          </Button>
          <Button
            type="default"
            icon={<FileTextOutlined />}
            onClick={handleReReview}
            style={{ borderRadius: 999 }}
            title="基于当前草稿重新审查"
          >
            基于草稿重新审查
          </Button>
        </Space>
      </div>

      <div
        style={{
          padding: '16px 18px',
          borderRadius: 24,
          border: '1px solid rgba(24,36,47,0.1)',
          background: 'rgba(255,255,255,0.9)',
          boxShadow: 'var(--shadow-md)',
        }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as 'edit' | 'preview')}
          items={[
            {
              key: 'edit',
              label: (
                <span>
                  <EditOutlined /> 编辑
                </span>
              ),
            },
            {
              key: 'preview',
              label: (
                <span>
                  <EyeOutlined /> 预览
                </span>
              ),
            },
          ]}
        />
      </div>

      <div
        style={{
          borderRadius: 24,
          border: '1px solid rgba(24,36,47,0.1)',
          background: 'rgba(255,255,255,0.9)',
          boxShadow: 'var(--shadow-md)',
          padding: 18,
        }}
      >
        {activeTab === 'edit' ? (
          <ContractEditor
            content={content}
            onChange={handleContentChange}
            editable
            placeholder="在此整理审查建议内容..."
          />
        ) : (
          <div
            style={{
              padding: '20px 24px',
              fontFamily: 'var(--font-serif)',
              fontSize: 15,
              lineHeight: 1.9,
              color: 'var(--ink)',
              minHeight: 400,
            }}
          >
            <div dangerouslySetInnerHTML={{ __html: content }} />
          </div>
        )}
      </div>

      {hasChanges && (
        <div
          style={{
            padding: '12px 18px',
            borderRadius: 20,
            background: 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)',
            border: '1px solid #fde68a',
            fontSize: 13,
            color: '#92400e',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>您有未保存的草稿更改（将保存到服务器）</span>
          <Button size="small" type="primary" onClick={handleSave}>
            保存草稿
          </Button>
        </div>
      )}

      <div
        style={{
          padding: '12px 18px',
          borderRadius: 20,
          background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
          border: '1px solid #bfdbfe',
          fontSize: 12,
          color: '#1e40af',
          lineHeight: 1.6,
        }}
      >
        <strong style={{ display: 'block', marginBottom: 4 }}>
          当前编辑模式说明
        </strong>
        <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
          <li>当前编辑的是从审查报告中提取的风险条款片段，不是完整合同原文</li>
          <li>草稿会自动保存到服务器，可跨会话恢复</li>
          <li>可直接基于当前草稿重新发起审查，生成新的审查结果</li>
        </ul>
      </div>
    </div>
  );
}
