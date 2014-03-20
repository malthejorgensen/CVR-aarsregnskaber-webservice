// var mApp = angular.module('mApp', ['ngRoute', 'ngResource']);
var mApp = angular.module('mApp', ['ngRoute', 'restangular']);

mApp.config(['$routeProvider', 'RestangularProvider', function($routeProvider, RestangularProvider) {
  $routeProvider
      .when('/', {
          templateUrl: '../static/home.html',
          controller: 'HomeController'
      })
      .when('/companies', {
          url: '../all.json'
          //controller: 'SecondController'
      })
      .when('/company/:cvr', {
          templateUrl: '../static/aarsregnskab.html',
          controller: 'AarsregnskabsController'
      })
      .otherwise({ redirectTo: '/' });


  // Now let's configure the response extractor for each request
  RestangularProvider.setRequestSuffix('.json');
  RestangularProvider.setResponseExtractor(function(response, operation, what, url) {
    // This is a get for a list
    console.log(response, operation, what, url);
    var newResponse;
    if (operation === "getList" && what == 'all') {
      // Here we're returning an Array which has one special property metadata with our extra information
      newResponse = response.companies;
    } else {
      newResponse = response;
    }
    return newResponse;
  });
}]);


// mApp.factory('Companies', ['$resource', function($resource) {
// // return $resource('/company/:cvr.json', null,
//   return $resource('/all.json', null, {
//       // 'get': { method: 'GET', isArray: true }
//     // 'query': { method:'GET', isArray: true }
//       // 'update': { method:'PUT' }
//   });
// }]);

mApp.controller('HomeController', ['$scope', 'Restangular', function ($scope, Restangular) {
// mApp.controller('HomeController', ['$scope', function ($scope) {
  // var Companies = $resource('/all.json', {userId:'@id'});
  var companies = Restangular.all('all').getList('companies'); //.$object;
  $scope.companies = companies.$object;
}]);

mApp.controller('AarsregnskabsController', ['$scope', '$routeParams', 'Restangular',
  function ($scope, $routeParams, Restangular) {
    var cvr = $routeParams.cvr;
    //var company = Restangular.all('company').get(cvr); //.$object;
    Restangular.one('company', cvr).get().then(function(company) {; //.$object;
      console.log(company);
      $scope.company = company;
      //$scope.fields = company.regnskaber[2011];
  });
  }
]);
