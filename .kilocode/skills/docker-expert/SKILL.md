---
name: docker-expert
description: Docker expertise. Containerization, Dockerfile optimization, Docker Compose, multi-stage builds, and production deployment patterns.
---

# Docker Expert

> Docker containerization for modern applications.
> **Learn to THINK, not copy fixed patterns.**

## 🎯 Selective Reading Rule

**Read ONLY files relevant to the request!** Check the content map, find what you need.

---

## 📑 Content Map

| File | Description | When to Read |
|------|-------------|--------------|
| `dockerfile.md` | Best practices, multi-stage, optimization | Writing Dockerfiles |
| `compose.md` | Multi-container, volumes, networking | Orchestrating services |
| `networking.md` | Bridge, overlay, host networks | Container communication |
| `volumes.md` | Bind mounts, named volumes, tmpfs | Data persistence |
| `optimization.md` | Image size, layer caching, build time | Performance tuning |
| `security.md` | Non-root users, secrets, scanning | Security best practices |
| `registry.md` | Docker Hub, ECR, GCR, private | Image distribution |

---

## 🏗️ Dockerfile Best Practices

### Multi-Stage Builds
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER node
CMD ["node", "dist/main.js"]
```

### Optimization Tips
1. Use specific tags (not `latest`)
2. Order instructions by change frequency
3. Use `.dockerignore` to exclude files
4. Run as non-root user
5. Use multi-stage builds for smaller images

---

## 📦 Docker Compose

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=secret

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

---

## 🔒 Security

1. **Never store secrets in images** - Use secrets management
2. **Run as non-root** - Add `USER` instruction
3. **Scan images** - Use `trivy` or `docker scout`
4. **Update base images** - Keep dependencies current
5. **Use minimal base images** - Alpine, distroless

---

## 🚀 Common Commands

```bash
# Build image
docker build -t myapp:latest .

# Run container
docker run -d -p 3000:3000 myapp:latest

# View logs
docker logs -f container_id

# Execute command in container
docker exec -it container_id sh

# Compose up
docker-compose up -d

# View logs
docker-compose logs -f
```

---

## 📚 Resources

- [Docker Documentation](https://docs.docker.com)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
