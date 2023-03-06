import axios from "axios";

const API_URL = "https://3fygxxklvb.execute-api.us-east-1.amazonaws.com/auth/";

class AuthService {
  login(email, password) {
    return axios
      .post(API_URL + "login", {
        email,
        password
      })
      .then(response => {
        if (response.data.token) {
          localStorage.setItem("token", response.data.token);
        }

        return response.data;
      });
  }

  logout() {
    localStorage.removeItem("token");
  }

  register(name, email, password) {
    return axios.post(API_URL + "register", {
      name,
      email,
      password
    });
  }


  getCurrentUser() {
    return localStorage.getItem('token');
  }
}

export default new AuthService();