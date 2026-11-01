angular.module('deciframeApp').controller('SequenciaController', function($http, $window, ngProgressFactory, $anchorScroll, $location, GENEROS, $uibModal) {
  var vm = this;
  vm.sequenciasFamosas = [];
  vm.erro = null;
  vm.novaSequencia = { acordes: [] };
  vm.minhaSequencia = {};
  vm.isSearching = false;
  vm.showSearchResultsCount = false;
  vm.esfigeSpeech =  "";
  vm.musics = [];
  vm.generos = GENEROS;
  vm.meuGenero = "";
  vm.progressbar = ngProgressFactory.createInstance();

  vm.carregarSequencias = function(){
    vm.erro = null;
    $http.get('/sequencias').success(function(data){
      var lista = data || [];
      vm.sequenciasFamosas = [];
      for (var i = 0; i < lista.length; i++) {
        var item = lista[i];
        var acordesObj = [];
        var acordesArr = item.acordes || [];
        for (var j = 0; j < acordesArr.length; j++) {
          acordesObj.push({ 'acorde': acordesArr[j], 'cor': '#2E1C74' });
        }
        vm.sequenciasFamosas.push({
          'index': i+1,
          'acordes': acordesObj,
          'origem': item.origem,
          'editavel': item.editavel,
          'id': item.id,
          'acordes_str': item.acordes_str
        });
      }
    }).error(function(){
      vm.erro = 'Erro ao carregar sequências do servidor.';
    });
  };

  vm.carregarSequencias();
  vm.minhaSequencia = {};
  vm.isSearching = false;
  vm.showSearchResultsCount = false;
  vm.esfigeSpeech =  "";
  vm.musics = [];
  vm.generos = GENEROS;
  vm.meuGenero = "";
  vm.progressbar = ngProgressFactory.createInstance();

  vm.temAcorde = function(acorde) {
    if (vm.minhaSequencia.acordes) {
      return (vm.minhaSequencia.acordes.indexOf(acorde) > -1);
    } else {
      return false;
    }
  }

  var createChordsString = function(chords) {
    var str = "";
    if(!chords){ return ""; }
    for (var i = 0; i < chords.length; i++) {
      var acordeStr = chords[i].acorde ? chords[i].acorde : chords[i];
      str = str.concat(acordeStr, ',');
    }
    if(str.length === 0){ return ""; }
    return str.substring(0, str.length-1);
  }

  vm.pesquisarPorSequencia = function(sequencia) {
    if (sequencia) {
      vm.minhaSequencia = sequencia;
    }
    vm.progressbar.start();
    vm.esfigeSpeech = "Procurando músicas com base na sequencia...";
    vm.isSearching = true;
    vm.musics = [];

    var apiUrl = "";
    var searchString = "similares?sequencia=".concat(createChordsString(vm.minhaSequencia.acordes));
    if (vm.meuGenero !== "" && vm.meuGenero !== null) {
      searchString += "&generos="+vm.meuGenero;
    }
    $http.get(apiUrl.concat(searchString))
      .success(function(data) {
        vm.progressbar.complete();
        vm.esfigeSpeech = "Encontrei essas músicas";
        vm.isSearching = false;
        vm.showSearchResultsCount = true;
        vm.musics = data;
      })
      .error(function(data) {
        vm.esfigeSpeech = "Ops! Algo errado.";
        vm.isSearching = false;
        vm.showSearchResultsCount = false;
      });
  }

  vm.adicionarAcordeNova = function(acorde){
    if(!acorde){ return; }
    if(!vm.novaSequencia.acordes){ vm.novaSequencia.acordes = []; }
    vm.novaSequencia.acordes.push({ 'acorde': acorde, 'cor': '#2E1C74' });
  };

  vm.removerUltimoNova = function(){
    if(vm.novaSequencia.acordes && vm.novaSequencia.acordes.length > 0){
      vm.novaSequencia.acordes.pop();
    }
  };

  vm.cadastrarSequencia = function(){
    vm.erro = null;
    if(!vm.novaSequencia.acordes || vm.novaSequencia.acordes.length < 2){
      vm.erro = 'Sequência precisa ter pelo menos 2 acordes.';
      return;
    }
    var lista = [];
    for (var i = 0; i < vm.novaSequencia.acordes.length; i++) {
      lista.push(vm.novaSequencia.acordes[i].acorde);
    }
    $http.post('/sequencias', {acordes: lista}).success(function(response){
      vm.novaSequencia = {acordes: []};
      vm.carregarSequencias();
    }).error(function(err){
      if(err && err.erro){
        vm.erro = err.erro;
      }else if(err && err.data && err.data.erro){
        vm.erro = err.data.erro;
      }else{
        vm.erro = 'Erro ao cadastrar sequência.';
      }
    });
  };

  vm.abrirModalCadastro = function(){
    var modalInstance = $uibModal.open({
      templateUrl: 'modalCadastroSequencia.html',
      controller: 'ModalCadastroSequenciaCtrl',
      controllerAs: 'SequenciaModal',
      resolve: {
        parent: function(){ return vm; }
      }
    });
    modalInstance.result.then(function(){
      vm.carregarSequencias();
    }, function(){});
  };

  vm.editarSequencia = function(sequencia){
    if(!sequencia.editavel || !sequencia.id){ return; }
    var atual = [];
    if(sequencia.acordes){
      for (var i = 0; i < sequencia.acordes.length; i++) {
        if(sequencia.acordes[i].acorde){
          atual.push(sequencia.acordes[i].acorde);
        }else if(typeof sequencia.acordes[i] === 'string'){
          atual.push(sequencia.acordes[i]);
        }
      }
    }
    var novo = prompt('Editar acordes (separados por vírgula):', atual.join(','));
    if(novo === null){ return; }
    var lista = novo.split(',').map(function(s){ return s.trim(); }).filter(function(s){ return s.length > 0; });
    $http.put('/sequencias/' + sequencia.id, {acordes: lista}).success(function(response){
      // rebuild sequencia object with new chords
      var novosObj = [];
      for (var j = 0; j < lista.length; j++) {
        novosObj.push({ 'acorde': lista[j], 'cor': '#2E1C74' });
      }
      vm.minhaSequencia = {
        index: sequencia.index,
        acordes: novosObj,
        origem: sequencia.origem,
        editavel: true,
        id: sequencia.id
      };
      vm.carregarSequencias();
      vm.pesquisarPorSequencia(vm.minhaSequencia);
    }).error(function(err){
      var msg = 'Erro ao editar sequência.';
      if(err && err.erro){ msg = err.erro; }
      else if(err && err.data && err.data.erro){ msg = err.data.erro; }
      alert(msg);
    });
  };

  vm.excluirSequencia = function(sequencia){
    if(!sequencia.editavel || !sequencia.id){ return; }
    if(!confirm('Excluir esta sequência?')){ return; }
    $http.delete('/sequencias/' + sequencia.id).success(function(response){
      if(vm.minhaSequencia && vm.minhaSequencia.id === sequencia.id){
        vm.minhaSequencia = {};
        vm.musics = [];
        vm.showSearchResultsCount = false;
      }
      vm.carregarSequencias();
    }).error(function(err){
      alert('Erro ao excluir sequência.');
    });
  };

  vm.limparPesquisa = function() {
    vm.minhaSequencia = {};
    vm.musics = [];
  }

  vm.goToLirics = function(music) {
    $window.open(music.url);
  };

  vm.goToResults = function() {
    vm.showSearchResultsCount = false;
    $("body").animate({scrollTop: $("#results").offset().top}, "slow");
  };
});


angular.module('deciframeApp').controller('ModalCadastroSequenciaCtrl', function($uibModalInstance, $http, parent){
  var vm = this;
  vm.novaSequencia = { acordes: [] };
  vm.erro = null;
  vm.novoAcorde = '';

  vm.adicionarAcordeNova = function(acorde){
    if(!acorde){ return; }
    if(!vm.novaSequencia.acordes){ vm.novaSequencia.acordes = []; }
    vm.novaSequencia.acordes.push({ 'acorde': acorde, 'cor': '#2E1C74' });
  };

  vm.removerUltimoNova = function(){
    if(vm.novaSequencia.acordes && vm.novaSequencia.acordes.length > 0){
      vm.novaSequencia.acordes.pop();
    }
  };

  vm.cadastrar = function(){
    vm.erro = null;
    if(!vm.novaSequencia.acordes || vm.novaSequencia.acordes.length < 2){
      vm.erro = 'Sequência precisa ter pelo menos 2 acordes.';
      return;
    }
    var lista = [];
    for (var i = 0; i < vm.novaSequencia.acordes.length; i++) {
      lista.push(vm.novaSequencia.acordes[i].acorde);
    }
    $http.post('/sequencias', {acordes: lista}).success(function(response){
      $uibModalInstance.close(response);
    }).error(function(err){
      if(err && err.erro){
        vm.erro = err.erro;
      }else if(err && err.data && err.data.erro){
        vm.erro = err.data.erro;
      }else{
        vm.erro = 'Erro ao cadastrar sequência.';
      }
    });
  };

  vm.cancelar = function(){
    $uibModalInstance.dismiss('cancel');
  };
});
