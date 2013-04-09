var dealer = angular.module('dealer', ['ngResource']);

dealer.factory('Task', function($resource){
    return $resource('/tasks/:id', {'id': '@id'});
});

dealer.controller('TasksCtrl', function($scope, Task){
    Task.get({}, function(response){
        $scope.tasks = response['tasks'];
    });

    $scope.taskClass = function(task) {
        return {
            warning: task.status == 'queued'
        }
    };
});

dealer.controller('AddCtrl', function($scope, $http, $location){
    $scope.request = {
        url: 'http://again.fm',
        consumer: 'playfm',
        content_type_limit: ['text/plain', 'text/html'],
        user_agent: 'Mozilla/5.0 (compatible; SpikeBot)',
        connect_timeout: 1,
        fetch_timeout: 1
    };

    $scope.submit = function() {
        var req = angular.copy($scope.request);
        if (angular.isArray(req.content_type_limit)) {
            req.content_type_limit = req.content_type_limit.join(',');
        }
        $http.post('/request', req).success(function(){
            $location.path('/tasks');
        }).error(function(data, status){
            $scope.error = status;
        });
    };
});

dealer.config(function($routeProvider, $locationProvider){
    $routeProvider.when('/', {redirectTo: '/tasks'});
    $routeProvider.when('/tasks', {controller: 'TasksCtrl', templateUrl: '/tasks.html'});
    $routeProvider.when('/tasks/add', {controller: 'AddCtrl', templateUrl: '/tasks-add.html'});
});

/*
admin.controller('AddCtrl', function($scope, Stream, $location){
    $scope.stream = {
        id: 'pianorama',
        url: 'http://pianorama.outself.ru/'
    };

    $scope.$watch('stream', function(){
        $scope.error = null;
    }, true);

    $scope.add = function() {
        Stream.save($scope.stream, function(){
            $location.path('/streams');
        }, function(http){
            $scope.error = http.status;
        });
    };
});
*/