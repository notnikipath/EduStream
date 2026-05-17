FROM node:20-alpine AS build

WORKDIR /app
COPY frontend/package.json ./package.json
RUN npm install
COPY frontend .
RUN npm run build

FROM python:3.11-alpine

WORKDIR /srv
COPY --from=build /app/dist /srv

EXPOSE 5176
CMD ["python", "-m", "http.server", "5176", "--bind", "0.0.0.0", "-d", "/srv"]
