import React, { Component } from "react";

import UserService from "../services/user.service";

export default class BoardUser extends Component {
  constructor(props) {
    super(props);

    this.state = {
      content: []
    };
  }

  componentDidMount() {
    UserService.getUserFavorites().then(
      response => {
        this.setState({
          content: response.data
        });
      },
      error => {
        this.setState({
          content:
            (error.response &&
              error.response.data &&
              error.response.data.message) ||
            error.message ||
            error.toString()
        });
      }
    );
  }

  render() {
    return (
      <div className="container">
        <header className="jumbotron">
          <h3>Favorites</h3>
          <ul className="list-group">
            
            {this.state.content.map(d => (
            <li className="list-group-item" key={d.title}>
              <button type="button" className="btn btn-danger btn-sm" onClick={function() {UserService.deleteUserFavorites(d.title)}}>X</button> 
              &nbsp; 
              <button type="button" className="btn btn-success btn-sm">Edit</button>  
              &nbsp; 
              {d.title}: {d.description}
              </li>
            ))} 
             
          </ul> 
          <br/>
          <button 
                className="btn btn-primary btn-block"
          >Add</button>
        </header>
      </div>
    );
  }
}