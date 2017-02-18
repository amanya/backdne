"""empty message

Revision ID: c03208593ef6
Revises: 7a27ef43e028
Create Date: 2017-02-18 13:04:30.230926

"""

# revision identifiers, used by Alembic.
revision = 'c03208593ef6'
down_revision = '7a27ef43e028'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('scores', sa.Column('is_exam', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('gender', sa.String(length=32), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'gender')
    op.drop_column('scores', 'is_exam')
    ### end Alembic commands ###