import axios from "axios";

const api = axios.create({
  baseURL:
    import.meta.env.MODE === "development"
      ? "http://localhost:8000" // when running frontend on host
      : "http://backend:8000",  // when running inside docker-compose
});

export default api;
