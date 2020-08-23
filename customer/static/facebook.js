/* global document, window, FB */
(function () {
  'use strict'

  /* SUPPORT FUNCTIONS */
  function error_response(data, prefix){
    document.getElementById('api-response').innerHTML = "Response: " + data.status + ' ' + data.statusText + ', Action: ' + prefix + '<br/>Content: ' + data.responseText
    // $('.api-response').html("Response: " + data.status + ' ' + data.statusText + ', Action: ' + prefix + '<br/>Content: ' + data.responseText);
  }

  function success_response(data){
    document.getElementById('api-response').innerHTML = "Response: OK<br/>Content: " + JSON.stringify(data)
    // $('.api-response').html("Response: OK<br/>Content: " + JSON.stringify(data));
  }

  function postForm(action, data){
    var httpRequest = new XMLHttpRequest();
    var formData = new FormData();

    for (var key in data) {
      formData.append(key, data[key])
    }

    httpRequest.onreadystatechange = function(){
      if ( this.readyState == 4 && this.status == 200 ) {
        success_response(this.responseText);
      } else {
        error_response(this.responseText, 'post response')
      }
    };

    httpRequest.open('post', action);
    httpRequest.send(formData);
  }

  // function postForm(action, data) {
  //   var f = document.createElement('form')
  //   f.method = 'POST'
  //   f.action = action
  //
  //   for (var key in data) {
  //     var d = document.createElement('input')
  //     d.type = 'hidden'
  //     d.name = key
  //     d.value = data[key]
  //     f.appendChild(d)
  //   }
  //   document.body.appendChild(f)
  //   f.submit()
  // }

  function setLocationHref(url) {
    if (typeof(url) === 'function') {
      url()
    } else {
      window.location.href = url
    }
  }
  /* END OF SUPPORT */

  var allauth = window.allauth = window.allauth || {}
  var fbSettings = JSON.parse(document.getElementById('allauth-facebook-settings').innerHTML)
  // {
  //   "appId": "762414111184191",
  //   "version": "v8.0",
  //   "initParams": {
  //     "appId": "762414111184191",
  //     "version": "v8.0"
  //   },
  //   "loginOptions": {
  //     "scope": "email"
  //    },
  //    "nextUrl": "{{ request.get_full_path }}",
  //    "loginByTokenUrl": "http://{{ store.domain }}/accounts/facebook/login/token/",
  //    "cancelUrl": "http://{{ store.domain }}/accounts/social/login/cancelled/",
  //    "logoutUrl": "http://{{ store.domain }}/accounts/logout/",
  //    "loginUrl": "http://{{ store.domain }}/accounts/facebook/login/",
  //    "errorUrl": "http://{{ store.domain }}/accounts/social/login/error/",
  //    "csrfToken": "{% csrf_token %}"
  // }

  var fbInitialized = false

  allauth.facebook = {

    init: function (opts) {
      this.opts = opts

      window.fbAsyncInit = function () {
        // window.fbAsyncInit is called as soon as SDK loads
        // call FB.init()
        console.log('ready')
        FB.init(opts.initParams)
        fbInitialized = true
        allauth.facebook.onInit()
      };

    },

    onInit: function () {
    },

    login: function () {
      var nextUrl = this.opts.nextUrl
      var action = 'authenticate' //'authenticate' | 'reauthorize' | 'reauthenticate' | 'rerequest'
      var self = this
      if (!fbInitialized) {
        // var url = this.opts.loginUrl + '?next=' + encodeURIComponent(nextUrl) + '&action=' + encodeURIComponent(action) + '&process=' + encodeURIComponent(process) + '&scope=' + encodeURIComponent(scope)
        // setLocationHref(url)
        return
      }
      if (action === 'reauthenticate' || action === 'rerequest' || action === 'reauthorize') {
        this.opts.loginOptions.auth_type = action
      }

      FB.login(function (response) {
        if (response.authResponse) {
          self.onLoginSuccess(response, nextUrl)
        } else if (response && response.status && ['not_authorized', 'unknown'].indexOf(response.status) > -1) {
          self.onLoginCanceled(response)
        } else {
          self.onLoginError(response)
        }
      }, self.opts.loginOptions)
    },

    onLoginCanceled: function (response) {
      // setLocationHref(this.opts.cancelUrl)
      error_response(response, 'login canceled')
    },

    onLoginError: function (/* response */) {
      // setLocationHref(this.opts.errorUrl)
      error_response(response, 'login error')
    },

    onLoginSuccess: function (response, nextUrl) {
      var data = {
        next: nextUrl || '',
        // process: 'login',
        access_token: response.authResponse.accessToken,
        expires_in: response.authResponse.expiresIn,
        csrfmiddlewaretoken: this.opts.csrfToken
      }

      postForm(this.opts.loginByTokenUrl, data)
    },

    logout: function (nextUrl) {
      var self = this
      if (!fbInitialized) {
        return
      }
      FB.logout(function (response) {
        self.onLogoutSuccess(response, nextUrl)
      })
    },

    onLogoutSuccess: function (response, nextUrl) {
      var data = {
        next: nextUrl || '',
        csrfmiddlewaretoken: this.opts.csrfToken
      }

      postForm(this.opts.logoutUrl, data)
    }
  }

  allauth.facebook.init(fbSettings)
})()