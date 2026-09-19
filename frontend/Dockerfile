# ============================================================================
# Dockerfile Frontend - Orchestrateur IA
# ============================================================================

FROM node:20-alpine as base

WORKDIR /app

# ============================================================================
# Stage Development
# ============================================================================
FROM base as development

# Copier package files
COPY package*.json ./

# Installer les dépendances
RUN npm install

# Copier le code (sera overridé par volume en dev)
COPY . .

# Port Vite
EXPOSE 5173

# Commande dev avec hot reload
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ============================================================================
# Stage Production
# ============================================================================
FROM base as production

# Copier package files
COPY package*.json ./

# Installer SEULEMENT les dépendances de production
RUN npm ci --only=production

# Copier le code
COPY . .

# Build de production
RUN npm run build

# Installer serve pour servir le build
RUN npm install -g serve

# Port
EXPOSE 3000

# Servir le build
CMD ["serve", "-s", "dist", "-l", "3000"]
