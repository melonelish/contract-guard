"""Check draft data for old separators and test markers."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import get_session_factory
from app.db.models import Contract, User, Tenant


async def check_drafts():
    """Query contracts with draft content containing old separator or test markers."""
    async_session = get_session_factory()

    async with async_session() as session:
        # Query all contracts with draft content
        stmt = select(Contract).where(Contract.draft_content.isnot(None))
        result = await session.execute(stmt)
        contracts_with_draft = result.scalars().all()

        print(f'总共有 {len(contracts_with_draft)} 个合同有草稿内容')
        print('=' * 80)

        old_separator_contracts = []
        test_marker_contracts = []

        for contract in contracts_with_draft:
            user = await session.get(User, contract.user_id)
            tenant = await session.get(Tenant, contract.tenant_id)

            draft_content = contract.draft_content or ''

            # Check for old separator
            has_old_separator = ' 路 ' in draft_content

            # Check for test markers
            has_test_marker = any(
                marker in draft_content.lower()
                for marker in ['test', '测试', 'demo', '验收']
            )

            if has_old_separator or has_test_marker:
                info = {
                    'id': str(contract.id),
                    'title': contract.title,
                    'user_email': user.email if user else '未知',
                    'tenant_name': tenant.name if tenant else '未知',
                    'has_old_separator': has_old_separator,
                    'has_test_marker': has_test_marker,
                    'draft_preview': draft_content[:300]
                }

                if has_old_separator:
                    old_separator_contracts.append(info)
                if has_test_marker:
                    test_marker_contracts.append(info)

                print(f'合同 ID: {info["id"]}')
                print(f'合同标题: {info["title"]}')
                print(f'用户邮箱: {info["user_email"]}')
                print(f'租户名称: {info["tenant_name"]}')
                print(f'包含旧分隔符: {info["has_old_separator"]}')
                print(f'包含测试标记: {info["has_test_marker"]}')
                print(f'草稿内容预览:')
                print(info["draft_preview"])
                print('-' * 80)

        print('\n')
        print('=' * 80)
        print(f'汇总: 包含旧分隔符的合同数: {len(old_separator_contracts)}')
        print(f'汇总: 包含测试标记的合同数: {len(test_marker_contracts)}')


if __name__ == '__main__':
    asyncio.run(check_drafts())
