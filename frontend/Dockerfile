FROM node:20-alpine

WORKDIR /app

# Install deps
COPY frontend/package*.json ./
RUN npm install

# Copy source
COPY frontend ./

EXPOSE 5173

# Run Vite dev server
CMD ["npm", "run", "dev", "--", "--host", "--port", "5173"]

