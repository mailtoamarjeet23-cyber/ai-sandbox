FROM node:22 AS build
WORKDIR /app

# --depth=1 skips full history — faster clone
RUN git clone --depth=1 https://github.com/medplum/medplum.git .

RUN npm ci

# Build only the server and its local workspace dependencies via Turborepo
RUN npx turbo build --filter=@medplum/server

FROM node:22
WORKDIR /app

COPY --from=build /app .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
