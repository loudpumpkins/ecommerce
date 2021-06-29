# e-commerce API
Backend Django API that can handle requests from multiple e-commerce stores with different domains.  
The idea is to have multiple React Apps (or any other front-end framework) hosted on Google's Cloud Platform and have all those apps access a single hosted API.  
Google buckets will serve the React App to the user using it's robust CDN. The end-user will only hit our weak server (compared to Google's servers) when making API calls.  
This should help pages load faster and improve user experience.  

[not a minimum viable product yet]  

## Steps to launch a new site

#### Register domain name with Google

#### Google Bucket

#### MailGun

* https://app.mailgun.com/app/sending/domains -> *add domain*  
* [missing dns setup steps]  
* setup all templates found in [*shop.models.notification.MailTemplate*]
* setup gmail SMTP  


#### Facebook Social Login

* https://developers.facebook.com/ -> *login to alexei_panov@hotmail.com*  
* *my apps* -> *ecommerce*
* *settings* -> *basic*
* in *app domains* add *[http(s)://domain.com]*

#### React Mobile

## python manage.py *[commands]*
