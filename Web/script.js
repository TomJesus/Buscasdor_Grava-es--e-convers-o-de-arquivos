// script.js
const btnBuscar = document.getElementById('btnBuscar');
const telefonesInput = document.getElementById('telefones');
const arquivoInput = document.getElementById('arquivoExcel');
const listaResultados = document.getElementById('listaResultados');
const logsBox = document.getElementById('logsBox');
const audioPlayer = document.getElementById('audioPlayer');

function addLog(msg){
  const el = document.createElement('div');
  el.textContent = msg;
  logsBox.appendChild(el);
  logsBox.scrollTop = logsBox.scrollHeight;
}

window.addLog = addLog; // backend chama webview.evaluate_js("window.addLog('msg')")

btnBuscar.addEventListener('click', async () => {
  const telefones = telefonesInput.value.trim();
  const arquivo = arquivoInput.files[0] ? arquivoInput.files[0].path : null;

 //addLog('🚀 Iniciando busca...');
  try {
    // chamar API.buscar (retorna lista de itens)
    const resultados = await window.pywebview.api.buscar(telefones, arquivo);
    renderResultados(resultados || []);
    addLog(`✅ Busca retornou ${ (resultados || []).length } itens.`);
  } catch (err) {
    addLog(`[ERRO] ${err}`);
  }
});

function renderResultados(items){
  listaResultados.innerHTML = '';
  if(!items || items.length === 0){
    listaResultados.innerHTML = '<div style="padding:8px;color:#9aa6b2">Nenhuma gravação encontrada.</div>';
    return;
  }
  items.forEach((it, i) => {
    const div = document.createElement('div');
    div.className = 'item';
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.innerHTML = `<div><strong>${it.instalacao}</strong> — ${it.nome}</div>
                      <div style="color:#9aa6b2">${it.telefone} • #${it.idx} • ${it.formato || 'desconhecido'}</div>
                      <div style="font-size:12px;color:#7f8a95;margin-top:6px">${it.caminho_original}</div>`;
    const actions = document.createElement('div');
    actions.className = 'actions';

    const btnPlay = document.createElement('button');
    btnPlay.className = 'btn play';
    btnPlay.textContent = '▶️ Ouvir';
    btnPlay.onclick = async () => {
    //addLog(`▶ Preparando reprodução: ${it.caminho_original}`);
    try {
    const audioUrl = await window.pywebview.api.preparar_play(it.caminho_original);
    if(audioUrl){
      //addLog(`▶ URL do áudio: ${audioUrl}`);

      // Para o áudio atual antes de carregar novo
      audioPlayer.pause();
      audioPlayer.currentTime = 0;

      // Define a nova fonte
      audioPlayer.src = audioUrl;

      // Tenta reproduzir
      const playPromise = audioPlayer.play();

      if (playPromise !== undefined) {
        playPromise.then(() => {
          addLog('▶ Reproduzindo áudio...');
        }).catch(e => {
          addLog(`[ERRO] Falha ao reproduzir: ${e.message}`);
        });
      }

    } else {
      addLog('[ERRO] Não foi possível preparar arquivo para play.');
    }
  } catch (err) {
    addLog(`[ERRO] Play: ${err}`);
  }
};

// Adicione event listeners para o player
audioPlayer.addEventListener('error', function(e) {
  addLog(`[ERRO] Player: ${audioPlayer.error ? audioPlayer.error.message : 'Erro desconhecido'}`);
});

audioPlayer.addEventListener('canplay', function() {
  //addLog('✅ Áudio carregado e pronto para reprodução');
});
    const btnSave = document.createElement('button');
    btnSave.className = 'btn save';
    btnSave.textContent = '💾 Salvar';
    btnSave.onclick = async () => {
      addLog(`💾 Salvando: ${it.caminho_original}`);
      const nomeSugerido = `${it.instalacao} - ${it.nome} - ${it.idx}.${it.formato === 'gsm' ? 'mp3' : it.formato}`;
      const salvo = await window.pywebview.api.salvar(it.caminho_original, nomeSugerido);
      if(salvo){
        addLog(`💾 Salvo em: ${salvo}`);
      } else {
        addLog('⚠ Salvamento cancelado/erro.');
      }
    };

    actions.appendChild(btnPlay);
    actions.appendChild(btnSave);
    div.appendChild(meta);
    div.appendChild(actions);
    listaResultados.appendChild(div);
  });
}
