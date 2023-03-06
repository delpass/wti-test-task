import axios from 'axios';
import authHeader from './auth-header';

const API_URL = 'https://3fygxxklvb.execute-api.us-east-1.amazonaws.com/';

class UserService {
  getPublicContent() {
    return axios.get(API_URL + '');
  }

  getUserFavorites() {
    return axios.get(API_URL + 'favorites', { headers: authHeader() });
  }

  deleteUserFavorites(title) {
    return axios.delete(API_URL + 'favorites/' + title, { headers: authHeader() });
  }

  getAdminBoard() {
    return axios.get(API_URL + 'admin', { headers: authHeader() });
  }
}

export default new UserService();