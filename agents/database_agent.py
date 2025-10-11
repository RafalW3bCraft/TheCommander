import os
import re
import logging
import subprocess
import json
import psycopg2
from typing import List, Dict, Any, Optional
from agents.base_agent import BaseAgent
from ai_service import ai_service

logger = logging.getLogger(__name__)

class DatabaseAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            name="DatabaseAgent",
            description="Specialized in database operations, SQL, and database security."
        )
        self.supported_db_types = [
            "postgresql", "mysql", "sqlite", "mongodb"
        ]
        
    def get_commands(self):
        return {
            "generate-schema": {
                "description": "Generate a database schema from description",
                "usage": "generate-schema <db_type> <description>",
                "examples": [
                    "generate-schema postgresql 'A blog with users, posts, and comments'",
                    "generate-schema sqlite 'A simple inventory tracking system'"
                ]
            },
            "optimize-query": {
                "description": "Optimize a SQL query for performance",
                "usage": "optimize-query <db_type> <query>",
                "examples": [
                    "optimize-query postgresql 'SELECT * FROM users JOIN posts ON users.id = posts.user_id'",
                    "optimize-query mysql 'SELECT * FROM products WHERE price > 100'"
                ]
            },
            "security-audit": {
                "description": "Perform a security audit on database setup or query",
                "usage": "security-audit <db_type> <query_or_schema>",
                "examples": [
                    "security-audit postgresql 'SELECT * FROM users WHERE username = \\'$input\\''",
                    "security-audit mysql 'CREATE USER \\'app\\'@\\'%\\' IDENTIFIED BY \\'password\\''"
                ]
            },
            "generate-migration": {
                "description": "Generate a database migration script",
                "usage": "generate-migration <db_type> <description>",
                "examples": [
                    "generate-migration postgresql 'Add email_verified column to users table'",
                    "generate-migration mysql 'Create new order_history table with foreign key to orders'"
                ]
            },
            "document-schema": {
                "description": "Generate documentation for a database schema",
                "usage": "document-schema <db_type> <schema>",
                "examples": [
                    "document-schema postgresql 'CREATE TABLE users (id SERIAL PRIMARY KEY, username VARCHAR(50), email VARCHAR(100) UNIQUE)'"
                ]
            }
        }
    
    def execute(self, command, args):
        try:
            if command == "generate-schema":
                if len(args) < 2:
                    return "Error: Missing database type or description. Usage: generate-schema <db_type> <description>"
                db_type = args[0].lower()
                description = " ".join(args[1:])
                return self._generate_schema(db_type, description)
            
            elif command == "optimize-query":
                if len(args) < 2:
                    return "Error: Missing database type or query. Usage: optimize-query <db_type> <query>"
                db_type = args[0].lower()
                query = " ".join(args[1:])
                return self._optimize_query(db_type, query)
                
            elif command == "security-audit":
                if len(args) < 2:
                    return "Error: Missing database type or query/schema. Usage: security-audit <db_type> <query_or_schema>"
                db_type = args[0].lower()
                query_or_schema = " ".join(args[1:])
                return self._security_audit(db_type, query_or_schema)
                
            elif command == "generate-migration":
                if len(args) < 2:
                    return "Error: Missing database type or description. Usage: generate-migration <db_type> <description>"
                db_type = args[0].lower()
                description = " ".join(args[1:])
                return self._generate_migration(db_type, description)
                
            elif command == "document-schema":
                if len(args) < 2:
                    return "Error: Missing database type or schema. Usage: document-schema <db_type> <schema>"
                db_type = args[0].lower()
                schema = " ".join(args[1:])
                return self._document_schema(db_type, schema)
                
            else:
                return f"Unknown command: '{command}'"
                
        except Exception as e:
            logger.error(f"Error in DatabaseAgent: {str(e)}")
            return f"Error executing command: {str(e)}"

    def _generate_schema(self, db_type, description):
        if db_type not in self.supported_db_types:
            return f"Error: Unsupported database type: {db_type}. Supported types: {', '.join(self.supported_db_types)}"
        
        try:
            try:
                system_prompt = f"""
                You are an expert database architect specializing in {db_type}.
                Generate a complete database schema based on the user's description.
                Include:
                
                1. All necessary tables with appropriate fields
                2. Primary and foreign keys
                3. Appropriate indexes for performance
                4. Data types suitable for {db_type}
                5. Constraints for data integrity
                
                Format your response with clear CREATE TABLE statements and comments explaining design decisions.
                Follow best practices for {db_type} database design.
                """
                
                if 'claude' in ai_service.models:
                    logger.debug(f"Using AI Service to generate {db_type} schema for: {description}")
                    response = ai_service.models['claude'].messages.create(
                        model="claude-3-5-sonnet-20241022",
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": f"Please design a {db_type} database schema for: {description}"}
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    ai_output = response.content[0].text
                    
                    result = f"{db_type.upper()} Schema for: {description}\n\n"
                    result += ai_output
                    return result
                    
            except Exception as ai_err:
                logger.warning(f"AI Service schema generation failed: {str(ai_err)}. Falling back to template schemas.")
            
            if db_type == "postgresql":
                if "blog" in description.lower():
                    schema = """CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE post_tags (
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);

CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_post_tags_tag_id ON post_tags(tag_id);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""
                elif "inventory" in description.lower() or "product" in description.lower():
                    schema = """CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    sku VARCHAR(50) UNIQUE,
    price DECIMAL(10, 2) NOT NULL,
    cost DECIMAL(10, 2),
    quantity INTEGER NOT NULL DEFAULT 0,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_suppliers (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    supply_price DECIMAL(10, 2),
    lead_time_days INTEGER,
    PRIMARY KEY (product_id, supplier_id)
);

CREATE TABLE inventory_transactions (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    reference_id VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_product_suppliers_supplier_id ON product_suppliers(supplier_id);
CREATE INDEX idx_inventory_transactions_product_id ON inventory_transactions(product_id);
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_quantity ON products(quantity);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON suppliers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION update_product_quantity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE products
    SET quantity = quantity + NEW.quantity
    WHERE id = NEW.product_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_inventory_transaction_insert AFTER INSERT ON inventory_transactions
    FOR EACH ROW EXECUTE FUNCTION update_product_quantity();
"""
                else:
                    schema = """CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_items_user_id ON items(user_id);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_items_updated_at BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""
            elif db_type == "mysql":
                if "blog" in description.lower():
                    schema = """CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    bio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    user_id INT NOT NULL,
    published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL,
    user_id INT NOT NULL,
    post_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
) ENGINE=InnoDB;

CREATE TABLE post_tags (
    post_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_post_tags_tag_id ON post_tags(tag_id);
"""
                else:
                    schema = """CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    user_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE INDEX idx_items_user_id ON items(user_id);
"""
            else:
                schema = f"""CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_items_user_id ON items(user_id);
"""
            
            result = f"{db_type.upper()} Schema for: {description}\n\n```sql\n{schema}\n```"
            return result
            
        except Exception as e:
            logger.error(f"Error generating schema: {str(e)}")
            return f"Error generating schema: {str(e)}"
            
    def _optimize_query(self, db_type, query):
        if db_type not in self.supported_db_types:
            return f"Error: Unsupported database type: {db_type}. Supported types: {', '.join(self.supported_db_types)}"
        
        try:
            try:
                system_prompt = f"""
                You are a database performance expert specializing in {db_type}.
                Analyze and optimize the provided SQL query.
                Consider:
                
                1. Proper indexing suggestions
                2. Query structure and joins
                3. Selection of columns (avoid SELECT *)
                4. Limiting result sets appropriately
                5. Proper use of WHERE clauses
                6. Usage of appropriate built-in functions
                
                Provide the optimized query and explain each optimization step.
                Include performance implications and reasoning.
                """
                
                if 'claude' in ai_service.models:
                    logger.debug(f"Using AI Service to optimize {db_type} query: {query}")
                    response = ai_service.models['claude'].messages.create(
                        model="claude-3-5-sonnet-20241022",
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": f"Please optimize this {db_type} query: {query}"}
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    ai_output = response.content[0].text
                    
                    result = f"Query Optimization for {db_type}:\n\n"
                    result += f"Original query:\n```sql\n{query}\n```\n\n"
                    result += ai_output
                    return result
                    
            except Exception as ai_err:
                logger.warning(f"AI Service query optimization failed: {str(ai_err)}. Falling back to basic optimization rules.")
            
            result = f"Query Optimization for {db_type}:\n\n"
            result += f"Original query:\n```sql\n{query}\n```\n\n"
            
            suggestions = []
            
            if "SELECT *" in query.upper():
                suggestions.append("Avoid using SELECT * - specify only the columns you need to reduce data transfer and improve performance.")
            
            if "WHERE" not in query.upper() and "SELECT" in query.upper() and "FROM" in query.upper():
                suggestions.append("Consider adding a WHERE clause to limit results if appropriate.")
            
            if "JOIN" in query.upper() and "ON" not in query.upper():
                suggestions.append("Ensure all JOINs have proper ON conditions to avoid cartesian products.")
            
            if "GROUP BY" in query.upper():
                suggestions.append("Ensure columns in GROUP BY have appropriate indexes.")
            
            if "ORDER BY" in query.upper():
                suggestions.append("Ensure columns in ORDER BY have appropriate indexes for better performance.")
            
            if "LIKE" in query.upper():
                suggestions.append("LIKE queries can be slow. If possible, use full-text search or exact matches. Avoid leading wildcards (e.g., LIKE '%value').")
            
            if suggestions:
                result += "Optimization Suggestions:\n"
                for i, suggestion in enumerate(suggestions, 1):
                    result += f"{i}. {suggestion}\n"
            else:
                result += "No obvious optimization opportunities detected. Consider using EXPLAIN to analyze query performance.\n"
            
            result += "\nGeneral Recommendations:\n"
            result += "1. Use EXPLAIN or EXPLAIN ANALYZE to understand query execution plans\n"
            result += "2. Create indexes on columns frequently used in WHERE, JOIN, and ORDER BY clauses\n"
            result += "3. Consider using database-specific optimization tools and profilers\n"
            result += "4. Monitor query performance in production and adjust indexes accordingly\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing query: {str(e)}")
            return f"Error optimizing query: {str(e)}"
    
    def _security_audit(self, db_type, query_or_schema):
        if db_type not in self.supported_db_types:
            return f"Error: Unsupported database type: {db_type}. Supported types: {', '.join(self.supported_db_types)}"
        
        try:
            try:
                system_prompt = f"""
                You are a database security expert specializing in {db_type}.
                Perform a security audit on the provided SQL query or schema.
                Look for:
                
                1. SQL injection vulnerabilities
                2. Weak authentication or authorization
                3. Insecure data storage practices
                4. Missing encryption for sensitive data
                5. Improper access controls
                6. Use of weak or default passwords
                
                Provide specific security issues found and recommendations to fix them.
                """
                
                if 'claude' in ai_service.models:
                    logger.debug(f"Using AI Service to audit {db_type} security")
                    response = ai_service.models['claude'].messages.create(
                        model="claude-3-5-sonnet-20241022",
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": f"Please perform a security audit on this {db_type} query/schema: {query_or_schema}"}
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    ai_output = response.content[0].text
                    
                    result = f"Security Audit for {db_type}:\n\n"
                    result += f"Query/Schema:\n```sql\n{query_or_schema}\n```\n\n"
                    result += ai_output
                    return result
                    
            except Exception as ai_err:
                logger.warning(f"AI Service security audit failed: {str(ai_err)}. Falling back to basic security checks.")
            
            result = f"Security Audit for {db_type}:\n\n"
            result += f"Query/Schema:\n```sql\n{query_or_schema}\n```\n\n"
            
            vulnerabilities = []
            
            if re.search(r"WHERE\s+\w+\s*=\s*['\"]?\$", query_or_schema, re.IGNORECASE):
                vulnerabilities.append("SQL Injection Risk: Direct string concatenation in WHERE clause. Use parameterized queries instead.")
            
            if re.search(r"password\s+VARCHAR\(\d+\)", query_or_schema, re.IGNORECASE):
                vulnerabilities.append("Weak Password Storage: Password field should use a proper hashing algorithm (e.g., bcrypt). Never store plaintext passwords.")
            
            if "IDENTIFIED BY 'password'" in query_or_schema:
                vulnerabilities.append("Weak Password: Default or weak password detected. Use strong, unique passwords.")
            
            if re.search(r"@'%'", query_or_schema):
                vulnerabilities.append("Overly Permissive Access: User can connect from any host. Restrict access to specific IP addresses when possible.")
            
            if "CREATE USER" in query_or_schema.upper() and "GRANT ALL" in query_or_schema.upper():
                vulnerabilities.append("Excessive Privileges: Granting ALL privileges is a security risk. Follow principle of least privilege.")
            
            if vulnerabilities:
                result += "Security Vulnerabilities Found:\n"
                for i, vuln in enumerate(vulnerabilities, 1):
                    result += f"{i}. {vuln}\n"
            else:
                result += "No obvious security vulnerabilities detected. However, this does not guarantee complete security.\n"
            
            result += "\nSecurity Best Practices:\n"
            result += "1. Always use parameterized queries to prevent SQL injection\n"
            result += "2. Hash passwords using strong algorithms (bcrypt, Argon2, etc.)\n"
            result += "3. Implement principle of least privilege for database users\n"
            result += "4. Encrypt sensitive data at rest and in transit\n"
            result += "5. Regularly update database software and apply security patches\n"
            result += "6. Implement proper access controls and authentication\n"
            result += "7. Enable database audit logging for sensitive operations\n"
            result += "8. Use SSL/TLS for database connections\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing security audit: {str(e)}")
            return f"Error performing security audit: {str(e)}"
    
    def _generate_migration(self, db_type, description):
        if db_type not in self.supported_db_types:
            return f"Error: Unsupported database type: {db_type}. Supported types: {', '.join(self.supported_db_types)}"
        
        try:
            try:
                system_prompt = f"""
                You are a database migration expert specializing in {db_type}.
                Generate a database migration script based on the description.
                Include:
                
                1. Proper ALTER TABLE or CREATE TABLE statements
                2. Data type specifications appropriate for {db_type}
                3. Constraints and indexes if needed
                4. Rollback script to undo the migration
                5. Comments explaining what the migration does
                
                Format your response with clear UP and DOWN migration scripts.
                """
                
                if 'claude' in ai_service.models:
                    logger.debug(f"Using AI Service to generate {db_type} migration for: {description}")
                    response = ai_service.models['claude'].messages.create(
                        model="claude-3-5-sonnet-20241022",
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": f"Please generate a {db_type} migration script for: {description}"}
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    ai_output = response.content[0].text
                    
                    result = f"Database Migration for {db_type}:\n\n"
                    result += f"Description: {description}\n\n"
                    result += ai_output
                    return result
                    
            except Exception as ai_err:
                logger.warning(f"AI Service migration generation failed: {str(ai_err)}. Falling back to basic migration template.")
            
            migration_up = ""
            migration_down = ""
            
            if "add" in description.lower() and "column" in description.lower():
                column_match = re.search(r'add\s+(\w+)\s+column\s+(?:to\s+)?(\w+)', description, re.IGNORECASE)
                if column_match:
                    column_name = column_match.group(1)
                    table_name = column_match.group(2)
                    
                    if db_type == "postgresql":
                        migration_up = f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(255);"
                        migration_down = f"ALTER TABLE {table_name} DROP COLUMN {column_name};"
                    elif db_type == "mysql":
                        migration_up = f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(255);"
                        migration_down = f"ALTER TABLE {table_name} DROP COLUMN {column_name};"
                    else:
                        migration_up = f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT;"
                        migration_down = f"ALTER TABLE {table_name} DROP COLUMN {column_name};"
            
            elif "create" in description.lower() and "table" in description.lower():
                table_match = re.search(r'create\s+(?:new\s+)?(\w+)\s+table', description, re.IGNORECASE)
                if table_match:
                    table_name = table_match.group(1)
                    
                    if db_type == "postgresql":
                        migration_up = f"""CREATE TABLE {table_name} (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);"""
                        migration_down = f"DROP TABLE {table_name};"
                    elif db_type == "mysql":
                        migration_up = f"""CREATE TABLE {table_name} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;"""
                        migration_down = f"DROP TABLE {table_name};"
                    else:
                        migration_up = f"""CREATE TABLE {table_name} (
    id INTEGER PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"""
                        migration_down = f"DROP TABLE {table_name};"
            
            else:
                migration_up = f"-- {description}\n-- TODO: Add your migration SQL here"
                migration_down = "-- TODO: Add rollback SQL here"
            
            result = f"Database Migration for {db_type}:\n\n"
            result += f"Description: {description}\n\n"
            result += "## UP Migration (Apply)\n\n```sql\n" + migration_up + "\n```\n\n"
            result += "## DOWN Migration (Rollback)\n\n```sql\n" + migration_down + "\n```\n\n"
            result += "## Usage:\n"
            result += "1. Review the migration SQL carefully\n"
            result += "2. Test on a development database first\n"
            result += "3. Backup your production database before applying\n"
            result += "4. Apply the UP migration to make changes\n"
            result += "5. Use DOWN migration to rollback if needed\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating migration: {str(e)}")
            return f"Error generating migration: {str(e)}"
    
    def _document_schema(self, db_type, schema):
        if db_type not in self.supported_db_types:
            return f"Error: Unsupported database type: {db_type}. Supported types: {', '.join(self.supported_db_types)}"
        
        try:
            try:
                system_prompt = f"""
                You are a technical documentation expert specializing in {db_type} databases.
                Generate comprehensive documentation for the provided database schema.
                Include:
                
                1. Overview of the schema and its purpose
                2. Detailed description of each table
                3. Column descriptions with data types
                4. Relationships between tables
                5. Indexes and constraints
                6. Usage examples or common queries
                
                Format your response in clear Markdown with sections and tables.
                """
                
                if 'claude' in ai_service.models:
                    logger.debug(f"Using AI Service to document {db_type} schema")
                    response = ai_service.models['claude'].messages.create(
                        model="claude-3-5-sonnet-20241022",
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": f"Please generate documentation for this {db_type} schema:\n{schema}"}
                        ],
                        temperature=0.1,
                        max_tokens=2500
                    )
                    ai_output = response.content[0].text
                    
                    result = f"Database Schema Documentation ({db_type}):\n\n"
                    result += ai_output
                    return result
                    
            except Exception as ai_err:
                logger.warning(f"AI Service schema documentation failed: {str(ai_err)}. Falling back to basic documentation.")
            
            result = f"Database Schema Documentation ({db_type}):\n\n"
            result += f"Original Schema:\n```sql\n{schema}\n```\n\n"
            
            tables = []
            current_table = None
            
            for line in schema.split('\n'):
                line = line.strip()
                
                if not line or line.startswith('--') or line.startswith('/*'):
                    continue
                
                if "CREATE TABLE" in line.upper():
                    table_match = re.search(r'CREATE TABLE [\"`]?(\w+)[\"`]?', line, re.IGNORECASE)
                    if table_match:
                        current_table = {
                            "name": table_match.group(1),
                            "columns": [],
                            "constraints": []
                        }
                        tables.append(current_table)
                
                elif current_table and line.startswith(');'):
                    current_table = None
                
                elif current_table and "," in line:
                    col_match = re.search(r'[\"`]?(\w+)[\"`]?\s+([^,]+)', line)
                    if col_match and not line.upper().startswith('PRIMARY KEY') and not line.upper().startswith('FOREIGN KEY'):
                        col_name = col_match.group(1)
                        col_type = col_match.group(2).strip()
                        current_table["columns"].append({
                            "name": col_name,
                            "type": col_type
                        })
                
                elif current_table and ("PRIMARY KEY" in line.upper() or "FOREIGN KEY" in line.upper() or "CONSTRAINT" in line.upper()):
                    current_table["constraints"].append(line.rstrip(','))
            
            result += "# Database Documentation\n\n"
            
            if tables:
                result += "## Tables Overview\n\n"
                for table in tables:
                    result += f"- **{table['name']}**: Contains {len(table['columns'])} columns\n"
                
                result += "\n## Table Details\n\n"
                for table in tables:
                    result += f"### {table['name']}\n\n"
                    
                    result += "#### Columns\n\n"
                    result += "| Column Name | Data Type | Description |\n"
                    result += "|-------------|-----------|-------------|\n"
                    for column in table["columns"]:
                        description = ""
                        if column["name"].lower() == "id":
                            description = "Primary identifier for the record"
                        elif "name" in column["name"].lower():
                            description = "Name or title"
                        elif "description" in column["name"].lower():
                            description = "Detailed description or information"
                        elif "created" in column["name"].lower() and "at" in column["name"].lower():
                            description = "Timestamp when the record was created"
                        elif "updated" in column["name"].lower() and "at" in column["name"].lower():
                            description = "Timestamp when the record was last updated"
                        elif "user" in column["name"].lower() and "id" in column["name"].lower():
                            description = "Reference to a user record"
                        elif "email" in column["name"].lower():
                            description = "Email address"
                        elif "password" in column["name"].lower():
                            description = "Hashed password (never store plaintext passwords)"
                        
                        result += f"| {column['name']} | {column['type']} | {description} |\n"
                    
                    if table["constraints"]:
                        result += "\n#### Constraints\n\n"
                        for constraint in table["constraints"]:
                            result += f"- `{constraint}`\n"
                    
                    result += "\n"
            else:
                result += "No table definitions found in the provided schema.\n"
            
            result += "\n## Relationships\n\n"
            result += "Relationships between tables should be defined by foreign key constraints. Please review the schema for specific relationships.\n\n"
            
            result += "## Performance Considerations\n\n"
            result += "- Ensure proper indexes are created for columns used in WHERE, JOIN, and ORDER BY clauses\n"
            result += "- Consider adding indexes for foreign key columns\n"
            result += "- Monitor query performance and adjust indexes as needed\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error documenting schema: {str(e)}")
            return f"Error documenting schema: {str(e)}"
