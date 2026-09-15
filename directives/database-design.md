---
name: database-design
description: Database design and querying skill covering relational databases (SQL, PostgreSQL, MySQL, SQLite), NoSQL (MongoDB), schema design, normalization, indexing, and ORMs. Use this skill when the user wants to design a database schema, write SQL queries, set up database tables, model relationships (one-to-many, many-to-many), optimize slow queries, or work with an ORM like Prisma, SQLAlchemy, or Mongoose. Also triggers for tasks like "design a database for my app", "write a query to get X", "set up my tables", "add an index", "model users and posts", or "what's the best DB structure for this?". Use even for partial tasks like writing a single query, adding a column, or explaining normalization.
---

# Database Design Skill

This skill covers designing clean, performant, and scalable database schemas and writing effective queries for SQL and NoSQL databases.

---

## Step 1: Choose the Right Database

| Situation | Recommended DB |
|---|---|
| Structured data with clear relationships | PostgreSQL (best default) |
| Simple/embedded app, local dev | SQLite |
| High-read web apps, legacy systems | MySQL |
| Flexible document structure, rapid prototyping | MongoDB |
| Key-value caching, sessions | Redis |
| Full-text search | Elasticsearch or PostgreSQL (with `tsvector`) |

**Default recommendation**: Use **PostgreSQL** unless there's a specific reason not to.

---

## Step 2: Schema Design Principles

### Normalization Rules (aim for 3NF)

1. **1NF**: No repeating groups. Every cell holds one atomic value.
2. **2NF**: No partial dependencies. Non-key columns depend on the whole primary key.
3. **3NF**: No transitive dependencies. Non-key columns depend only on the primary key, not on each other.

### Practical Rule of Thumb
- If data is repeated across rows → extract it into its own table
- If you find yourself storing comma-separated values in a column → that's a relationship, model it properly
- Don't over-normalize: sometimes denormalization is intentional for performance

---

## Step 3: Common Relationship Patterns

### One-to-Many (e.g., User → Posts)
```sql
CREATE TABLE users (
  id        SERIAL PRIMARY KEY,
  email     VARCHAR(255) UNIQUE NOT NULL,
  name      VARCHAR(100) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE posts (
  id        SERIAL PRIMARY KEY,
  user_id   INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title     VARCHAR(255) NOT NULL,
  body      TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Many-to-Many (e.g., Students ↔ Courses)
```sql
CREATE TABLE students (
  id   SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL
);

CREATE TABLE courses (
  id    SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL
);

-- Junction table
CREATE TABLE enrollments (
  student_id INT REFERENCES students(id) ON DELETE CASCADE,
  course_id  INT REFERENCES courses(id) ON DELETE CASCADE,
  enrolled_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (student_id, course_id)
);
```

### One-to-One (e.g., User → Profile)
```sql
CREATE TABLE profiles (
  id       SERIAL PRIMARY KEY,
  user_id  INT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  bio      TEXT,
  avatar   VARCHAR(500)
);
```

---

## Step 4: Data Types Guide

| Use Case | PostgreSQL Type | MySQL Type |
|---|---|---|
| Short text (name, email) | `VARCHAR(n)` | `VARCHAR(n)` |
| Long text (bio, body) | `TEXT` | `TEXT` |
| Integer IDs | `SERIAL` / `BIGSERIAL` | `INT AUTO_INCREMENT` |
| Decimal prices | `NUMERIC(10,2)` | `DECIMAL(10,2)` |
| Timestamps | `TIMESTAMP` | `DATETIME` |
| Boolean | `BOOLEAN` | `TINYINT(1)` |
| UUID | `UUID` | `CHAR(36)` |
| JSON data | `JSONB` | `JSON` |

---

## Step 5: Essential SQL Queries

### CRUD Operations
```sql
-- Create
INSERT INTO users (email, name) VALUES ('alice@example.com', 'Alice');

-- Read with JOIN
SELECT p.title, u.name AS author
FROM posts p
JOIN users u ON p.user_id = u.id
WHERE u.id = 1
ORDER BY p.created_at DESC;

-- Update
UPDATE users SET name = 'Alice Smith' WHERE id = 1;

-- Delete
DELETE FROM posts WHERE id = 5;
```

### Aggregations
```sql
-- Count posts per user
SELECT u.name, COUNT(p.id) AS post_count
FROM users u
LEFT JOIN posts p ON p.user_id = u.id
GROUP BY u.id, u.name
ORDER BY post_count DESC;
```

### Pagination
```sql
-- Page 2, 10 items per page
SELECT * FROM posts
ORDER BY created_at DESC
LIMIT 10 OFFSET 10;
```

### Subquery
```sql
-- Users who have written more than 5 posts
SELECT * FROM users
WHERE id IN (
  SELECT user_id FROM posts
  GROUP BY user_id
  HAVING COUNT(*) > 5
);
```

---

## Step 6: Indexing

### When to add indexes
- Columns used in `WHERE`, `JOIN ON`, `ORDER BY` frequently
- Foreign key columns (most ORMs do this automatically — verify!)
- Columns used in `UNIQUE` constraints

### Creating indexes
```sql
-- Single column
CREATE INDEX idx_posts_user_id ON posts(user_id);

-- Compound (order matters — put equality columns first)
CREATE INDEX idx_posts_user_created ON posts(user_id, created_at DESC);

-- Unique
CREATE UNIQUE INDEX idx_users_email ON users(email);
```

### When NOT to index
- Small tables (full scan is fine)
- Columns with very low cardinality (e.g., a `status` column with 2 values)
- Columns rarely used in filtering

---

## Step 7: ORM Usage

### Prisma (Node.js)
```prisma
model User {
  id    Int    @id @default(autoincrement())
  email String @unique
  posts Post[]
}

model Post {
  id     Int  @id @default(autoincrement())
  author User @relation(fields: [authorId], references: [id])
  authorId Int
}
```
```js
const posts = await prisma.post.findMany({
  where: { authorId: 1 },
  orderBy: { createdAt: 'desc' },
  take: 10,
});
```

### SQLAlchemy (Python)
```python
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    posts = relationship('Post', back_populates='author')
```

---

## Step 8: MongoDB Schema Design

MongoDB is schemaless, but still design intentionally.

### Embed vs. Reference
- **Embed** (nested document): When data is always read together, data is owned by parent, and the embedded data is small and bounded.
- **Reference** (store `_id`): When data is shared across documents, the nested array could grow unboundedly, or you need to query the nested data independently.

```js
// Embed (post with comments — bounded, always read together)
{
  _id: ObjectId(),
  title: "My Post",
  comments: [
    { user: "Alice", text: "Great!", createdAt: ISODate() }
  ]
}

// Reference (post with author — author is shared)
{
  _id: ObjectId(),
  title: "My Post",
  authorId: ObjectId("user123")
}
```

---

## Step 9: Common Mistakes to Avoid

- ❌ Storing passwords in plain text
- ❌ Using `SELECT *` in production queries
- ❌ Not indexing foreign keys
- ❌ Storing arrays as comma-separated strings
- ❌ Using `TEXT` for everything instead of appropriate types
- ❌ No `ON DELETE` behavior specified on foreign keys
- ❌ No timestamps (`created_at`, `updated_at`) on important tables
- ❌ Soft deletes without an index on `deleted_at`

---

## Output Format

When providing database designs:
- Show full `CREATE TABLE` SQL for relational databases
- Include sample data inserts where helpful
- Explain the reasoning behind key design decisions
- Note any trade-offs made
