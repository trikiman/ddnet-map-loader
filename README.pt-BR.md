# DDNet Map Loader v2 (Portátil)

Ferramenta simples para dar duplo clique em qualquer `.map` e recarregá‑lo no seu servidor local do DDNet. Também faz backups e registra logs.

## 📋 Requisitos
- Windows 10/11 (sem admin)
- Cliente/servidor DDNet instalados e servidor local acessível

## 🤔 O que é e por quê
- Associa arquivos `.map` a este app.
- Ao dar duplo clique em um mapa, ele:
  - Valida o arquivo
  - Faz backup do mapa atual
  - Substitui o mapa de trabalho e envia `hot_reload`
  - Escreve em `%APPDATA%\DDNet\maps\ddnet_control.log`
- Ótimo para iterar rápido enquanto mapeia.

## 🚀 Como usar (Rápido)
1) Verifique/mova `myServerconfig.cfg`
   - Copie para a pasta `data` (recomendado; veja detalhes abaixo).
2) Associe `.map` a este EXE (método recomendado)
   - Clique direito em um `.map` → Abrir com → Escolher outro aplicativo → Mais aplicativos → Procurar outro aplicativo neste PC
   - Selecione `ddnet_control.exe` nesta pasta
   - Marque “Sempre usar este aplicativo para abrir .map”
   - Verifique se o ícone de `.map` mudou; se não, veja a seção de problemas.
   - Avançado (opcional): execute `registry\setup_map_association_current_user.bat` e reinicie o Explorador.
3) Dê duplo clique em qualquer `.map`
   - Ex.: `%APPDATA%\DDNet\maps\mapsfortest\anymap.map`
4) Confira os logs
   - `%APPDATA%\DDNet\maps\ddnet_control.log`

## 📁 Onde colocar o myServerconfig.cfg
- Maneira simples de achar a pasta `data` do DDNet:
  1) Clique com o botão direito no atalho do DDNet (barra de tarefas/Iniciar/Área de trabalho) → Abrir local do arquivo
  2) Na pasta aberta, vá para `ddnet` (onde está `DDNet.exe`)
  3) Abra `data` → copie `myServerconfig.cfg` ali
- Locais comuns (exemplos):
  - Steam padrão: `C:\Program Files (x86)\Steam\steamapps\common\DDraceNetwork\ddnet\data`
  - Outra biblioteca Steam: `<SuaBibliotecaSteam>\steamapps\common\DDraceNetwork\ddnet\data`
  - Não‑Steam/portátil: pasta `data` ao lado do `DDNet.exe`

## 🧰 Problemas comuns
- Janela abre e fecha rápido
  - Geralmente o caminho do arquivo não foi passado. Refaça a associação (passo 2) e reinicie o Explorador.
- Não aparece em “Abrir com”
  - Use “Procurar outro aplicativo neste PC” e escolha `ddnet_control.exe`; marque “Sempre usar…”.
- Ícone não mudou
  - Reinicie o Explorador do Windows (cache de ícones).
- Sem hot‑reload
  - Garanta servidor em `127.0.0.1:8303` e RCON correto. Veja o log.
- Remover associação
  - `registry\remove_map_association_current_user.bat`

## 📂 Conteúdo
- `ddnet_control.exe`
- `ddnet_loader.ico`
- `myServerconfig.cfg`
- `registry/`
  - `setup_map_association_current_user.bat`
  - `remove_map_association_current_user.bat`