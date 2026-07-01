---
name: prisma-expert
description: Prisma ORM expertise. Schema design, migrations, queries, relations, transactions, and best practices for TypeScript/Node.js applications.
---

# Prisma Expert

> Prisma ORM expertise for TypeScript/Node.js applications.
> **Learn to THINK, not copy fixed patterns.**

## 🎯 Selective Reading Rule

**Read ONLY files relevant to the request!** Check the content map, find what you need.

---

## 📑 Content Map

| File | Description | When to Read |
|------|-------------|--------------|
| `schema.md` | Schema.prisma syntax, types, attributes | Defining data models |
| `relations.md` | One-to-one, one-to-many, many-to-many | Modeling relationships |
| `queries.md` | CRUD operations, filtering, pagination | Data retrieval |
| `migrations.md` | Migration workflow, troubleshooting | Schema changes |
| `transactions.md` | Interactive transactions, batch operations | Data consistency |
| `aggregations.md` | Count, sum, avg, groupBy, having | Analytics queries |
| `raw-queries.md` | Raw SQL, stored procedures | Complex queries |
| `performance.md` | Indexes, query optimization | Performance tuning |

---

## 🏗️ Schema Design

### Basic Types
```prisma
model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  name      String?
  posts     Post[]
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

### Relations
```prisma
// One-to-many
model Post {
  id       Int    @id @default(autoincrement())
  author   User   @relation(fields: [authorId], references: [id])
  authorId Int
}

// Many-to-many
model Post {
  tags Tag[]
}

model Tag {
  posts Post[]
}
```

---

## 📊 Common Queries

### Basic CRUD
```typescript
// Create
const user = await prisma.user.create({
  data: { email: 'test@example.com', name: 'Test' }
});

// Read
const users = await prisma.user.findMany({
  where: { email: { contains: '@example.com' } },
  orderBy: { createdAt: 'desc' }
});

// Update
const updated = await prisma.user.update({
  where: { id: 1 },
  data: { name: 'New Name' }
});

// Delete
await prisma.user.delete({ where: { id: 1 } });
```

### Relations
```typescript
// Include relations
const userWithPosts = await prisma.user.findUnique({
  where: { id: 1 },
  include: { posts: true }
});

// Nested writes
const user = await prisma.user.create({
  data: {
    email: 'test@example.com',
    posts: {
      create: [{ title: 'Hello World' }]
    }
  }
});
```

---

## 🚀 Performance Tips

1. **Use select** - Only fetch needed fields
2. **Use include wisely** - Avoid over-fetching
3. **Add indexes** - For frequently filtered fields
4. **Use cursor-based pagination** - For large datasets
5. **Batch queries** - Use `$transaction` for multiple writes

---

## 📚 Resources

- [Prisma Documentation](https://www.prisma.io/docs)
- [Prisma GitHub](https://github.com/prisma/prisma)
