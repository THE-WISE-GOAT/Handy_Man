"""Added table for categories

Revision ID: 582dd0e56fac
Revises: 851060d28cd1
Create Date: 2026-06-30 16:26:43.884986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '582dd0e56fac'
down_revision: Union[str, Sequence[str], None] = '851060d28cd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("booking_chats", sa.Column("categories", JSONB, nullable=True))
 
    op.execute(
        """
        UPDATE booking_chats
        SET categories = CASE
            WHEN problem_category IS NOT NULL AND problem_category != '' THEN
                jsonb_build_array(
                    jsonb_build_object(
                        'category', problem_category,
                        'tags', COALESCE(to_jsonb(service_tags), '[]'::jsonb),
                        'is_custom_category', COALESCE(is_custom_category, false)
                    )
                )
            ELSE '[]'::jsonb
        END
        """
    )
 
    op.drop_column("booking_chats", "problem_category")
    op.drop_column("booking_chats", "service_tags")
    op.drop_column("booking_chats", "is_custom_category")
 
 
def downgrade() -> None:
    op.add_column("booking_chats", sa.Column("problem_category", sa.String(), nullable=True))
    op.add_column("booking_chats", sa.Column("service_tags", sa.ARRAY(sa.String()), nullable=True))
    op.add_column(
        "booking_chats",
        sa.Column("is_custom_category", sa.Boolean(), server_default="false", nullable=False),
    )
 
    op.execute(
        """
        UPDATE booking_chats
        SET problem_category = categories->0->>'category',
            service_tags = ARRAY(SELECT jsonb_array_elements_text(categories->0->'tags')),
            is_custom_category = COALESCE((categories->0->>'is_custom_category')::boolean, false)
        WHERE categories IS NOT NULL AND jsonb_array_length(categories) > 0
        """
    )
 
    op.drop_column("booking_chats", "categories")
