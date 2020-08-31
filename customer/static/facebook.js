/* global document, window, FB */
(function () {
  'use strict'

  /* SUPPORT FUNCTIONS */
  function error_response(data, prefix){
    var message = document.createElement('div').innerHTML = "Response: "+prefix+"<br/>Content: " + data
    document.getElementById('api-response').after(message)
    // $('.api-response').html("Response: " + data.status + ' ' + data.statusText + ', Action: ' + prefix + '<br/>Content: ' + data.responseText);
  }

  function success_response(data){
    var message = document.createElement('p').innerHTML = "Response: OK<br/>Content: " + data
    document.getElementById('api-response').after(message)
    // $('.api-response').html("Response: OK<br/>Content: " + JSON.stringify(data));
  }

  function postForm(action, data){
    var httpRequest = new XMLHttpRequest();
    var formData = new FormData();

    for (var key in data) {
      formData.append(key, data[key])
    }

    httpRequest.onreadystatechange = function(){
      allauth.response = this
      if ( this.readyState == 4 && this.status == 200 ) {
        success_response(this.responseText);
      } else {
        error_response(this.responseText, this.statusText)
      }
    };

    httpRequest.open('post', action);
    httpRequest.send(formData);
  }
  /* END OF SUPPORT */

  var allauth = window.allauth = window.allauth || {}
  var fbSettings = JSON.parse(document.getElementById('allauth-facebook-settings').innerHTML)
  // "initParams": {
  //   "appId": "762414111184191",
  //   "version": "v8.0"
  // },
  // "loginOptions": {
  //   "scope": "email,public_profile"
  //  },
  //  "loginByTokenUrl": "{% url 'customer:fb-login-api' %}",
  //  "logoutUrl": "http://{{ store.domain }}/accounts/logout/",
  //  "csrfToken": "{{ csrf_token }}"

  var fbInitialized = false

  allauth.facebook = {

    init: function (opts) {
      this.opts = opts

      window.fbAsyncInit = function () {
        // window.fbAsyncInit is called as soon as SDK loads
        // call FB.init()
        FB.init(opts.initParams)
        fbInitialized = true
        allauth.facebook.onInit()
      };

    },

    onInit: function () {
      // init method - empty for now
    },

    login: function () {
      var action = 'authenticate' //'authenticate' | 'reauthorize' | 'reauthenticate' | 'rerequest'
      var self = this
      if (!fbInitialized) {
        console.log('Attempted to login before FB SDK was ready. Please wait.')
        return
      }
      if (action === 'reauthenticate' || action === 'rerequest' || action === 'reauthorize') {
        this.opts.loginOptions.auth_type = action
      }

      FB.login(function (response) {
        if (response.authResponse) {
          self.onLoginSuccess(response)
        } else if (response && response.status && ['not_authorized', 'unknown'].indexOf(response.status) > -1) {
          self.onLoginCanceled(response)
        } else {
          self.onLoginError(response)
        }
      }, self.opts.loginOptions)
    },

    onLoginCanceled: function (response) {
      console.log('Login cancelled. response: '+ JSON.stringify(response))
    },

    onLoginError: function (response) {
      console.log('Login error. response: '+ JSON.stringify(response))
    },

    onLoginSuccess: function (response) {
      console.log('Login success. response: '+ JSON.stringify(response))
      var data = {
        access_token: response.authResponse.accessToken,
        expires_in: response.authResponse.expiresIn,
        csrfmiddlewaretoken: this.opts.csrfToken
      }

      postForm(this.opts.loginByTokenUrl, data)
    },

    logout: function () {
      var self = this
      if (!fbInitialized) {
        return
      }
      FB.logout(function (response) {
        self.onLogoutSuccess(response)
      })
    },

    onLogoutSuccess: function (response) {
      console.log('Logout success. response: '+ JSON.stringify(response))
      var data = {
        csrfmiddlewaretoken: this.opts.csrfToken
      }

      postForm(this.opts.logoutUrl, data)
    }
  }

  allauth.facebook.init(fbSettings)
})()