# narrate

Selecione um texto em qualquer lugar do computador, aperte um atalho e ouça em voz alta, em **português do Brasil**.

Feito para quem usa agentes de IA no terminal (Claude Code, Codex e outros): as respostas costumam ser longas e cansam a vista. Com o `narrate`, você seleciona a resposta e escuta.

- 🔒 **100% local:** usa o modelo [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), que roda no seu computador. Nada é enviado para a internet.
- 🇧🇷 **Vozes em pt-BR:** `pf_dora` (feminina, padrão), `pm_alex` e `pm_santa` (masculinas).
- 🧹 **Lê só o que interessa:** ignora blocos de código e símbolos de markdown (`**`, `#`, tabelas, links).
- ⚡ **Leve:** não precisa de placa de vídeo; a voz começa em menos de 1 segundo.
- 🤖 **Última resposta do agente:** com o terminal do Claude Code ou do Codex em foco, o atalho lê a última resposta, sem precisar selecionar nada.
- ⏹️ **Liga e desliga no mesmo atalho:** apertar de novo interrompe a leitura.

> **Sistemas suportados:** Linux, com Wayland ou X11. Testado no Arch Linux com Hyprland ([Omarchy](https://omarchy.org/)). Deve funcionar em outras distribuições e desktops (GNOME, KDE, Sway), mas ainda não foi testado neles. macOS e Windows ainda não são suportados.

---

## Instalação

São 5 passos. Leva uns 5 minutos, a maior parte esperando o download do modelo.

### Passo 1: instale as dependências do sistema

Você precisa de:

- **espeak-ng:** converte o texto em fonemas do português.
- **PortAudio:** toca o áudio.
- **Uma ferramenta para ler a seleção:** `wl-clipboard` no Wayland ou `xclip` no X11. Na dúvida, instale as duas.
- **libnotify** (opcional): mostra avisos na tela, como "Nenhum texto selecionado".

Escolha o comando da sua distribuição:

```bash
# Arch Linux, Manjaro, EndeavourOS, Omarchy
sudo pacman -S espeak-ng portaudio wl-clipboard xclip libnotify

# Ubuntu, Debian, Linux Mint, Pop!_OS
sudo apt install espeak-ng libportaudio2 wl-clipboard xclip libnotify-bin

# Fedora
sudo dnf install espeak-ng portaudio wl-clipboard xclip libnotify
```

> Não sabe se usa Wayland ou X11? Rode `echo $XDG_SESSION_TYPE`.

### Passo 2: instale o uv

O [uv](https://docs.astral.sh/uv/) instala o `narrate` num ambiente isolado e baixa a versão certa do Python sozinho, sem mexer no Python do sistema.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Feche e abra o terminal depois de instalar. Confira com `uv --version`.

### Passo 3: instale o narrate

```bash
git clone https://github.com/DevJanderson/narrate.git
cd narrate
uv tool install .
```

Isso cria o comando `narrate` em `~/.local/bin`. Confira com `narrate --help`.

> Se aparecer "command not found", rode `uv tool update-shell` e abra um novo terminal.

### Passo 4: baixe o modelo de voz

```bash
narrate --download-model
```

São cerca de 340 MB, salvos em `~/.local/share/narrate/`. Só precisa fazer isso uma vez.

### Passo 5: faça o primeiro teste

Ligue o som e rode:

```bash
narrate --text "Olá! Eu sou a Dora. Se você está me ouvindo, a instalação deu certo."
```

Ouviu? Então está tudo pronto. Agora vale configurar o [atalho de teclado](#atalho-de-teclado), que é onde o `narrate` mostra a que veio.

---

## Como usar

| O que você quer | Comando |
|---|---|
| Ler o texto selecionado com o mouse | `narrate` |
| Ler um texto específico | `narrate --text "Seu texto aqui"` |
| Ler a saída de outro comando | `cat arquivo.md \| narrate` |
| Parar a leitura | `narrate --stop` (ou rodar `narrate` de novo) |
| Trocar a voz | `narrate --voice pm_alex` |
| Mudar a velocidade (0.5 a 2.0) | `narrate --speed 1.2` |

**Exemplo com agentes de IA:** ouvir a resposta direto, sem precisar selecionar nada:

```bash
claude -p "explique o que é um git rebase" | narrate
```

### O que o `narrate` lê quando você aperta o atalho

Sem `--text` e sem entrada padrão (que é o caso do atalho de teclado), ele decide nesta ordem:

1. **Você selecionou um texto novo?** Lê o texto selecionado. Funciona em qualquer programa.
2. **Senão, a janela em foco é um terminal com Claude Code ou Codex?** Lê a **última resposta** do agente. Veja como configurar em [Ler a última resposta do agente](#ler-a-última-resposta-do-agente-claude-code-e-codex).
3. **Senão,** mostra o aviso "Nada para ler".

"Texto novo" quer dizer diferente do último que o `narrate` leu. A seleção do Linux continua valendo depois de usada, então sem essa regra o atalho leria para sempre o mesmo trecho antigo.

### Como funciona a seleção

O `narrate` lê a **seleção primária** do Linux: o texto que você destaca com o mouse, mesmo sem dar Ctrl+C. É o mesmo texto que aparece quando você cola com o botão do meio do mouse. Funciona em terminais, navegadores, editores, leitores de PDF e na maioria dos programas.

Por segurança, ele **não** lê a área de transferência (Ctrl+C). Assim, uma senha copiada nunca é lida em voz alta por engano.

---

## Ler a última resposta do agente (Claude Code e Codex)

Com isso configurado, você não precisa selecionar a resposta: deixe o terminal do agente em foco e aperte o atalho. **Nada é lido automaticamente.** O agente só guarda a última resposta, e ela só é lida quando você aperta o atalho.

Funciona assim: ao terminar cada resposta, o agente roda `narrate --save-reply` (um *hook* `Stop`), que guarda o texto num arquivo temporário em `$XDG_RUNTIME_DIR/narrate/`. Quando você aperta o atalho, o `narrate` vê qual janela está em foco e lê a resposta mais recente de um agente rodando dentro dela.

### Claude Code

Adicione o hook ao seu `~/.claude/settings.json`. Se o arquivo já tiver uma seção `"hooks"` ou `"Stop"`, **acrescente** este item à lista existente em vez de substituí-la:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.local/bin/narrate --save-reply",
            "async": true
          }
        ]
      }
    ]
  }
}
```

Vale a partir da próxima sessão do Claude Code. Para conferir, use o comando `/hooks` dentro dele.

### Codex

Crie o arquivo `~/.codex/hooks.json` com o mesmo conteúdo acima. Se ele já existir, acrescente o item à lista `"Stop"`.

Na primeira vez, o Codex **pede que você aprove o hook**: abra o Codex, digite `/hooks` e aprove o hook do `narrate`. Sem isso, ele não roda. Testado no Codex 0.167.1.

### Limitações

- **Só no Hyprland, por enquanto:** é por ele que o `narrate` descobre a janela em foco. Em outros desktops, o atalho continua lendo a seleção normalmente.
- **Vários agentes na mesma janela** (painéis de tmux, tuios etc.): o atalho lê a resposta mais recente entre eles. Se quiser ouvir a de outro painel, selecione o texto.

### Voz e velocidade padrão

Para não repetir `--voice` e `--speed` toda vez, defina as variáveis no seu `~/.bashrc` (ou `~/.zshrc`):

```bash
export NARRATE_VOICE=pm_alex
export NARRATE_SPEED=1.1
```

No atalho de teclado, é mais simples passar as opções direto no comando (veja abaixo).

---

## Atalho de teclado

O jeito mais prático de usar o `narrate`: **selecione o texto → aperte o atalho → ouça. Aperte de novo para parar.**

Os exemplos usam `Super + Alt + R`; troque por outra combinação se ela já estiver em uso. Para usar outra voz no atalho, acrescente as opções ao comando, por exemplo `~/.local/bin/narrate --voice pm_alex`.

<details>
<summary><b>Omarchy</b></summary>

Adicione ao final de `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + ALT + R", "Read selection aloud", "~/.local/bin/narrate")
```

O Hyprland recarrega sozinho ao salvar.
</details>

<details>
<summary><b>Hyprland</b> (configuração em <code>hyprland.conf</code>)</summary>

Adicione a `~/.config/hypr/hyprland.conf`:

```ini
bind = SUPER ALT, R, exec, ~/.local/bin/narrate
```
</details>

<details>
<summary><b>Sway / i3</b></summary>

Adicione a `~/.config/sway/config` (ou `~/.config/i3/config`):

```
bindsym $mod+Mod1+r exec ~/.local/bin/narrate
```

Depois recarregue com `swaymsg reload` (ou `i3-msg reload`).
</details>

<details>
<summary><b>GNOME</b></summary>

1. Abra **Configurações → Teclado → Atalhos de teclado → Ver e personalizar atalhos**.
2. Vá em **Atalhos personalizados** e clique em **+**.
3. Preencha:
   - **Nome:** `Ler seleção em voz alta`
   - **Comando:** `/home/SEU-USUARIO/.local/bin/narrate` (o GNOME não entende `~`, use o caminho completo; descubra o seu com `echo $HOME`)
   - **Atalho:** aperte `Super + Alt + R`
</details>

<details>
<summary><b>KDE Plasma</b></summary>

1. Abra **Configurações do Sistema → Teclado → Atalhos**.
2. Clique em **Adicionar novo → Comando ou script**.
3. Em comando, coloque `/home/SEU-USUARIO/.local/bin/narrate` e defina o atalho `Super + Alt + R`.
</details>

---

## Uso de recursos

Medido num notebook com Intel Core Ultra 5 125H, sem placa de vídeo dedicada:

- **Velocidade:** gera o áudio cerca de 2,5× mais rápido do que o tempo de fala.
- **Início:** a voz começa em menos de 1 segundo. O resto é gerado enquanto ela fala.
- **CPU:** no máximo 4 núcleos, com prioridade baixa, para não atrapalhar o que você estiver fazendo.
- **Memória:** até ~750 MB, **só enquanto lê**. Ao terminar, o processo fecha e libera tudo.

---

## Solução de problemas

| Mensagem ou sintoma | O que fazer |
|---|---|
| `Modelo não encontrado` | Rode `narrate --download-model`. |
| `Não consegui ler a seleção` | Instale `wl-clipboard` (Wayland) ou `xclip` (X11). Veja o [Passo 1](#passo-1-instale-as-dependências-do-sistema). |
| `Nada para ler` | Selecione um texto com o mouse ou deixe em foco o terminal do agente. Para a última resposta funcionar, o hook precisa estar configurado e o agente precisa ter respondido pelo menos uma vez depois disso. |
| A última resposta do Codex não é lida | Confira se você aprovou o hook com `/hooks` dentro do Codex. |
| Não sai som | Confira se o áudio está saindo pelo dispositivo certo (fone, caixa de som). O `narrate` usa a saída padrão do sistema. |
| Erro mencionando `espeak` | Confira se o `espeak-ng` está instalado (`espeak-ng --version`). |
| Erro mencionando `PortAudio` | Instale o PortAudio (veja o [Passo 1](#passo-1-instale-as-dependências-do-sistema)). |
| O atalho não faz nada | Rode `narrate` no terminal com um texto selecionado para ver a mensagem de erro. Confira também se o caminho no atalho está certo (`which narrate`). |
| Termos em inglês saem com pronúncia estranha | É uma limitação conhecida: a voz é em português, então "deploy" ou "commit" são lidos como se fossem palavras em português. |

---

## Desinstalar

```bash
uv tool uninstall narrate
rm -rf ~/.local/share/narrate
```

Lembre de remover também o atalho de teclado e os hooks do `narrate` no Claude Code (`~/.claude/settings.json`) e no Codex (`~/.codex/hooks.json`), se tiver configurado.

---

## Licença

[MIT](LICENSE). O modelo Kokoro não faz parte deste repositório: ele é baixado à parte pelo `narrate --download-model` e tem licença própria (Apache 2.0).

## Créditos

- [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M): o modelo de voz (licença Apache 2.0).
- [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx): roda o Kokoro sem precisar de PyTorch (licença MIT).
- [eSpeak NG](https://github.com/espeak-ng/espeak-ng): converte o texto em fonemas (licença GPL-3.0).
