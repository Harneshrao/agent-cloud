FROM node:20

WORKDIR /app

# So Next.js dev server listens on all interfaces (required for Docker port mapping)
ENV HOSTNAME=0.0.0.0
ENV HOST=0.0.0.0
ENV PORT=3000

COPY package.json package-lock.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
