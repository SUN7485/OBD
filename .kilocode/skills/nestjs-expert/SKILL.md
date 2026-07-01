---
name: nestjs-expert
description: NestJS framework expertise. Modules, dependency injection, decorators, microservices, authentication, and best practices for building scalable Node.js applications.
---

# NestJS Expert

> NestJS framework expertise for building scalable Node.js applications.
> **Learn to THINK, not copy fixed patterns.**

## 🎯 Selective Reading Rule

**Read ONLY files relevant to the request!** Check the content map, find what you need.

---

## 📑 Content Map

| File | Description | When to Read |
|------|-------------|--------------|
| `modules.md` | Module system, feature modules, shared modules | Organizing application structure |
| `dependency-injection.md` | DI containers, providers, scopes | Understanding NestJS DI |
| `controllers.md` | Route handling, request/response, params | Building API endpoints |
| `providers.md` | Services, factory providers, async providers | Business logic implementation |
| `guards.md` | Auth guards, roles, permissions | Protecting routes |
| `interceptors.md` | Response transformation, logging | Middleware for transformation |
| `filters.md` | Exception handling, custom errors | Error handling |
| `pipes.md` | Validation, transformation | Input validation |
| `middleware.md` | Request/response modification | Custom middleware |
| `microservices.md` | TCP, Redis, MQTT, gRPC | Building microservices |
| `websockets.md` | Gateway, rooms, events | Real-time applications |
| `testing.md` | Unit tests, e2e, mocking | Testing NestJS apps |

---

## 🏗️ Architecture Principles

### Module-Based Design
- Each feature should be in its own module
- Use `SharedModule` for shared providers
- Use `CoreModule` for singletons
- Use `ConfigModule` for configuration

### Dependency Injection
- Prefer constructor injection
- Use `@Injectable()` decorator
- Understand provider scopes (default, request, transient)
- Use forward references for circular dependencies

### Controllers
- Keep controllers thin - delegate to services
- Use proper HTTP method decorators
- Handle params with pipes for validation
- Return DTOs, not entities

### Services
- One service per feature/domain
- Use transactions for data consistency
- Handle async operations properly
- Log important operations

---

## 🔧 Common Patterns

### Authentication
```typescript
// Use guards for route protection
@UseGuards(JwtAuthGuard)
@Controller('protected')
export class ProtectedController {}
```

### Validation
```typescript
// Use class-validator with pipes
@Post()
@UsePipes(new ValidationPipe())
create(@Body() createDto: CreateDto) {}
```

### Error Handling
```typescript
// Use exception filters
@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {}
```

---

## 📚 Resources

- [NestJS Documentation](https://docs.nestjs.com)
- [NestJS GitHub](https://github.com/nestjs/nest)
