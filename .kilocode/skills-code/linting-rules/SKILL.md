---
name: linting-rules
description: Code linting rules and validation patterns. ESLint, Prettier, TypeScript checks, and code quality enforcement for consistent codebases.
---

# Linting Rules

> Code linting rules and validation patterns for consistent codebases.
> **Learn to THINK, not copy fixed rules.**

---

## 🎯 When to Use

Use this skill when:
- Setting up linting for a new project
- Fixing linting errors
- Configuring code quality checks
- Adding pre-commit hooks

---

## 📋 Common Tools

### ESLint
```javascript
// .eslintrc.js
module.exports = {
  extends: ['eslint:recommended'],
  rules: {
    'no-unused-vars': 'error',
    'no-console': 'warn'
  }
};
```

### Prettier
```json
// .prettierrc
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5"
}
```

---

## 🔧 Pre-commit Hooks

```yaml
# .husky/pre-commit
npm run lint
npm run test
npm run type-check
```

---

## 📚 Resources

- [ESLint Documentation](https://eslint.org)
- [Prettier Documentation](https://prettier.io)
