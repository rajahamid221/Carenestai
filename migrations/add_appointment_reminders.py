from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///healthcare_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

def get_existing_columns():
    with app.app_context():
        result = db.engine.execute("PRAGMA table_info(user_settings)")
        return [row[1] for row in result]

def upgrade():
    with app.app_context():
        # Get existing columns
        existing_columns = get_existing_columns()
        all_columns = [
            'id', 'user_id', 'email_notifications', 'app_notifications',
            'appointment_reminders', 'two_factor_auth', 'data_encryption',
            'theme', 'font_size', 'data_retention', 'auto_backup',
            'created_at', 'updated_at'
        ]
        # Create new table with all columns
        db.engine.execute('''
            CREATE TABLE user_settings_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                email_notifications BOOLEAN DEFAULT TRUE,
                app_notifications BOOLEAN DEFAULT TRUE,
                appointment_reminders BOOLEAN DEFAULT TRUE,
                two_factor_auth VARCHAR(20) DEFAULT 'disabled',
                data_encryption BOOLEAN DEFAULT FALSE,
                theme VARCHAR(20) DEFAULT 'light',
                font_size VARCHAR(20) DEFAULT 'medium',
                data_retention INTEGER DEFAULT 90,
                auto_backup BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Prepare columns for insert
        insert_columns = [col for col in all_columns if col != 'appointment_reminders']
        select_parts = []
        for col in insert_columns:
            if col in existing_columns:
                select_parts.append(col)
            else:
                # Provide default values for missing columns
                if col == 'email_notifications' or col == 'app_notifications':
                    select_parts.append('TRUE AS ' + col)
                elif col == 'two_factor_auth':
                    select_parts.append("'disabled' AS two_factor_auth")
                elif col == 'data_encryption' or col == 'auto_backup':
                    select_parts.append('FALSE AS ' + col)
                elif col == 'theme':
                    select_parts.append("'light' AS theme")
                elif col == 'font_size':
                    select_parts.append("'medium' AS font_size")
                elif col == 'data_retention':
                    select_parts.append('90 AS data_retention')
                elif col == 'created_at' or col == 'updated_at':
                    select_parts.append('CURRENT_TIMESTAMP AS ' + col)
                else:
                    select_parts.append('NULL AS ' + col)
        select_clause = ', '.join(select_parts)
        db.engine.execute(f'''
            INSERT INTO user_settings_new (
                {', '.join(insert_columns)}
            )
            SELECT {select_clause} FROM user_settings
        ''')
        # Drop old table and rename new table
        db.engine.execute('DROP TABLE user_settings')
        db.engine.execute('ALTER TABLE user_settings_new RENAME TO user_settings')

def downgrade():
    with app.app_context():
        # Create new table without appointment_reminders
        db.engine.execute('''
            CREATE TABLE user_settings_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                email_notifications BOOLEAN DEFAULT TRUE,
                app_notifications BOOLEAN DEFAULT TRUE,
                two_factor_auth VARCHAR(20) DEFAULT 'disabled',
                data_encryption BOOLEAN DEFAULT FALSE,
                theme VARCHAR(20) DEFAULT 'light',
                font_size VARCHAR(20) DEFAULT 'medium',
                data_retention INTEGER DEFAULT 90,
                auto_backup BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Prepare columns for insert (excluding appointment_reminders)
        insert_columns = [col for col in all_columns if col != 'appointment_reminders']
        existing_columns = get_existing_columns()
        select_parts = []
        for col in insert_columns:
            if col in existing_columns:
                select_parts.append(col)
            else:
                # Provide default values for missing columns
                if col == 'email_notifications' or col == 'app_notifications':
                    select_parts.append('TRUE AS ' + col)
                elif col == 'two_factor_auth':
                    select_parts.append("'disabled' AS two_factor_auth")
                elif col == 'data_encryption' or col == 'auto_backup':
                    select_parts.append('FALSE AS ' + col)
                elif col == 'theme':
                    select_parts.append("'light' AS theme")
                elif col == 'font_size':
                    select_parts.append("'medium' AS font_size")
                elif col == 'data_retention':
                    select_parts.append('90 AS data_retention')
                elif col == 'created_at' or col == 'updated_at':
                    select_parts.append('CURRENT_TIMESTAMP AS ' + col)
                else:
                    select_parts.append('NULL AS ' + col)
        select_clause = ', '.join(select_parts)
        db.engine.execute(f'''
            INSERT INTO user_settings_new (
                {', '.join(insert_columns)}
            )
            SELECT {select_clause} FROM user_settings
        ''')
        # Drop old table and rename new table
        db.engine.execute('DROP TABLE user_settings')
        db.engine.execute('ALTER TABLE user_settings_new RENAME TO user_settings')

if __name__ == '__main__':
    upgrade() 