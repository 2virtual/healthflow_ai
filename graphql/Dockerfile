FROM node:20

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 4000

CMD ["node", "index.js"]





# # Use official Node.js image
# FROM node:20

# WORKDIR /app

# # Copy package files and install dependencies
# COPY package*.json ./
# RUN npm install

# # Copy GraphQL code
# COPY . .

# # Expose GraphQL port
# EXPOSE 4000

# # Start Apollo server
# CMD ["node", "index.js"]
