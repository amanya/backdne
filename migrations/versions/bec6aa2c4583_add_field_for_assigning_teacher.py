"""add field for assigning teacher

Revision ID: bec6aa2c4583
Revises: c03208593ef6
Create Date: 2017-08-16 16:49:37.609345

"""

# revision identifiers, used by Alembic.
revision = 'bec6aa2c4583'
down_revision = 'c03208593ef6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('teacher_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'users', 'users', ['teacher_id'], ['id'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'teacher_id')
    ### end Alembic commands ###
