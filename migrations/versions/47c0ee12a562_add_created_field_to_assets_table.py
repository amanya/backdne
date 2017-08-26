"""add created field to assets table

Revision ID: 47c0ee12a562
Revises: 2113da98e6fe
Create Date: 2017-08-26 14:52:00.685442

"""

# revision identifiers, used by Alembic.
revision = '47c0ee12a562'
down_revision = '2113da98e6fe'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('assets', sa.Column('created', sa.DateTime(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('assets', 'created')
    ### end Alembic commands ###
