"""Clean test draft data with old separators."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import get_session_factory
from app.db.models import Contract, User


async def clean_test_drafts():
    """Clear draft content for smoke test contracts containing old separators."""
    async_session = get_session_factory()

    async with async_session() as session:
        # Query contracts with draft content
        stmt = select(Contract).where(Contract.draft_content.isnot(None))
        result = await session.execute(stmt)
        contracts = result.scalars().all()

        cleaned_count = 0

        for contract in contracts:
            draft_content = contract.draft_content or ''

            # Only clean if:
            # 1. Contains old separator ' 路 '
            # 2. Belongs to smoke test user
            if ' 路 ' in draft_content:
                user = await session.get(User, contract.user_id)

                # Verify it's smoke test data
                if user and user.email == 'smoke@test.com':
                    print(f'清理测试草稿:')
                    print(f'  合同 ID: {contract.id}')
                    print(f'  合同标题: {contract.title}')
                    print(f'  用户邮箱: {user.email}')
                    print(f'  草稿长度: {len(draft_content)} 字符')

                    # Clear draft content
                    contract.draft_content = None
                    contract.draft_updated_at = None

                    cleaned_count += 1
                    print(f'  [OK] 已清空草稿内容')
                    print('-' * 80)
                else:
                    print(f'跳过非测试数据:')
                    print(f'  合同 ID: {contract.id}')
                    print(f'  用户邮箱: {user.email if user else "未知"}')
                    print(f'  原因: 不是 smoke@test.com 用户')
                    print('-' * 80)

        if cleaned_count > 0:
            await session.commit()
            print(f'\n[OK] 已清理 {cleaned_count} 个测试草稿')
        else:
            print('\n未找到需要清理的测试草稿')


if __name__ == '__main__':
    print('开始清理测试草稿数据...')
    print('=' * 80)
    asyncio.run(clean_test_drafts())
