M<% import re %>
"""<%%= re.sub(r'^.+_', '', re.sub(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}_', '', filename)) %> — Auto-generated migration.

Revision ID: <%%= up_revision %>
Revises: <%%= down_revision | comma,n %>
Create Date: <%%= create_date %>
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
<%%- if upgrades.get("upgrades") %>
<%%+ for upgrade in upgrades.get("upgrades", {}).get("", []) %>
<%%+ endfor %>
<%%- endif %>

# revision identifiers, used by Alembic.
revision: str = "<%%= up_revision %>"
down_revision: Union[str, None] = "<%%= down_revision %>"
branch_labels: Union[str, Sequence[str], None] = <%%= repr(branch_labels) %>
depends_on: Union[str, Sequence[str], None] = <%%= repr(depends_on) %>


def upgrade() -> None:
    <%%- if upgrades.get("upgrades") %>
    <%%+ for upgrade in upgrades.get("upgrades", {}).get("", []) %>
    <%%- if upgrade.replace("(", "", 1)[0:1] in ("'", '"') %>
    <%%+ else %>
    <%%+ endif %>
    <%%- endfor %>
    <%%- endif %>
    <%%- if downgrades.get("downgrades") %>
    op.<%%= downgrades["downgrades"][0].strip() %>
    <%%- endif %>


def downgrade() -> None:
    <%%- if downgrades.get("downgrades") %>
    <%%+ for downgrade in downgrades.get("downgrades", {}).get("", []) %>
    <%%- if downgrade.replace("(", "", 1)[0:1] in ("'", '"') %>
    <%%+ else %>
    <%%+ endif %>
    <%%- endfor %>
    <%%- endif %>
