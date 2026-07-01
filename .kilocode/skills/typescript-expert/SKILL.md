---
name: typescript-expert
description: TypeScript expertise. Advanced types, generics, decorators, performance patterns, and type-level programming for building type-safe applications.
---

# TypeScript Expert

> Advanced TypeScript for building type-safe applications.
> **Learn to THINK, not copy fixed patterns.**

## 🎯 Selective Reading Rule

**Read ONLY files relevant to the request!** Check the content map, find what you need.

---

## 📑 Content Map

| File | Description | When to Read |
|------|-------------|--------------|
| `generics.md` | Generic constraints, defaults, inference | Reusable type-safe code |
| `utility-types.md` | Partial, Required, Pick, Omit, etc. | Type transformations |
| `conditional-types.md` | Infer, extends, distributive | Type-level logic |
| `mapped-types.md` | Key remapping, modifiers | Type transformations |
| `decorators.md` | Class, method, property decorators | Meta-programming |
| `module-augmentation.md` | Global types, namespace merging | Extending types |
| `performance.md` | Type instantiation, complexity | Large codebase optimization |

---

## 🏗️ Advanced Types

### Generic Constraints
```typescript
// Constrain to specific type
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// Default generic types
interface ApiResponse<T = unknown> {
  data: T;
  status: number;
}
```

### Conditional Types
```typescript
// Type inference
type ReturnType<T> = T extends (...args: infer A) => infer R ? R : never;

// Distributive conditional
type NonNullable<T> = T extends null | undefined ? never : T;
```

### Mapped Types
```typescript
// Readonly mapped type
type Readonly<T> = {
  readonly [P in keyof T]: T[P];
};

// Pick specific keys
type Pick<T, K extends keyof T> = {
  [P in K]: T[P];
};
```

---

## 🎨 Utility Types

```typescript
// Make all properties optional
type Partial<T>

// Make all properties required
type Required<T>

// Pick specific properties
type Pick<T, K extends keyof T>

// Omit specific properties
type Omit<T, K extends keyof T>

// Make all properties readonly
type Readonly<T>

// Extract return type
type ReturnType<T extends (...args: any) => any>

// Extract parameter types
type Parameters<T extends (...args: any) => any>
```

---

## ⚡ Performance Patterns

1. **Avoid circular type dependencies** - Can cause infinite type instantiation
2. **Use type inference** - Let TypeScript infer when possible
3. **Cache complex types** - Store as named types
4. **Prefer interfaces for objects** - Faster than types for extendability
5. **Use `const` assertions** - For literal types

---

## 📚 Resources

- [TypeScript Documentation](https://www.typescriptlang.org/docs)
- [TypeScript GitHub](https://github.com/Microsoft/TypeScript)
