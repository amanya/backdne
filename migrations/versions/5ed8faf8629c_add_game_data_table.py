"""add game_data table

Revision ID: 5ed8faf8629c
Revises: 47c0ee12a562
Create Date: 2017-08-30 21:02:25.823075

"""

# revision identifiers, used by Alembic.
revision = '5ed8faf8629c'
down_revision = '47c0ee12a562'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('game_data',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_name', sa.String(length=128), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_game_data_file_name'), 'game_data', ['file_name'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_game_data_file_name'), table_name='game_data')
    op.drop_table('game_data')
    ### end Alembic commands ###
