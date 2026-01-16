# Generated manually to fix django_admin_log foreign key constraint

from django.db import migrations


def cleanup_orphaned_admin_logs(apps, schema_editor):
    """
    Delete orphaned admin log entries that reference non-existent users.
    This happens when django_admin_log still references auth_user 
    but the project uses a custom user model.
    """
    db_alias = schema_editor.connection.alias
    
    # Delete admin log entries that reference non-existent users using raw SQL
    with schema_editor.connection.cursor() as cursor:
        # Delete orphaned records - users that don't exist in users_user table
        cursor.execute("""
            DELETE FROM django_admin_log 
            WHERE user_id IS NOT NULL 
            AND user_id NOT IN (SELECT id FROM users_user)
        """)


def drop_old_constraint(apps, schema_editor):
    """
    Drop the old foreign key constraint that points to auth_user.
    Find the constraint name dynamically.
    """
    with schema_editor.connection.cursor() as cursor:
        # First, try to drop the specific constraint from the error message
        specific_constraints = [
            'django_admin_log_user_id_c564eba6_fk_auth_user_id',
            'django_admin_log_user_id_fk_auth_user_id',
        ]
        
        for constraint_name in specific_constraints:
            try:
                cursor.execute(f"""
                    ALTER TABLE django_admin_log 
                    DROP CONSTRAINT IF EXISTS {constraint_name} CASCADE
                """)
            except Exception:
                pass  # Constraint might not exist, continue
        
        # Find all foreign key constraints on user_id column that reference auth_user
        cursor.execute("""
            SELECT 
                tc.constraint_name,
                ccu.table_name as referenced_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu 
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.table_name = 'django_admin_log' 
            AND tc.constraint_type = 'FOREIGN KEY'
            AND kcu.column_name = 'user_id'
            AND tc.table_schema = current_schema()
        """)
        
        constraints = cursor.fetchall()
        for constraint_name, ref_table in constraints:
            # Drop the constraint if it references auth_user
            if ref_table and 'auth_user' in ref_table:
                try:
                    cursor.execute(f"""
                        ALTER TABLE django_admin_log 
                        DROP CONSTRAINT IF EXISTS {constraint_name} CASCADE
                    """)
                except Exception:
                    pass  # Constraint might already be dropped


def create_new_constraint(apps, schema_editor):
    """
    Create new foreign key constraint pointing to custom user model.
    """
    with schema_editor.connection.cursor() as cursor:
        # Check if constraint already exists
        cursor.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'django_admin_log' 
            AND constraint_name = 'django_admin_log_user_id_fk_users_user_id'
        """)
        
        if not cursor.fetchone():
            # Create new foreign key constraint
            cursor.execute("""
                ALTER TABLE django_admin_log 
                ADD CONSTRAINT django_admin_log_user_id_fk_users_user_id 
                FOREIGN KEY (user_id) 
                REFERENCES users_user(id) 
                ON DELETE CASCADE
            """)


def reverse_migration(apps, schema_editor):
    """Reverse migration - drop the new constraint"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE django_admin_log 
            DROP CONSTRAINT IF EXISTS django_admin_log_user_id_fk_users_user_id CASCADE
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_user_is_staff_user_is_superuser'),
        ('admin', '0001_initial'),  # Ensure admin app is migrated
    ]

    operations = [
        # First, clean up orphaned records
        migrations.RunPython(cleanup_orphaned_admin_logs, migrations.RunPython.noop),
        
        # Drop the old foreign key constraint
        migrations.RunPython(drop_old_constraint, migrations.RunPython.noop),
        
        # Create new foreign key constraint pointing to custom user model
        migrations.RunPython(create_new_constraint, reverse_migration),
    ]
