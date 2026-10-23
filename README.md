# Atlas de Leituras — Streamlit + atualização automática no GitHub

Este projeto transforma o Atlas em um app Streamlit com formulário de cadastro. Quando o app está configurado, cada livro enviado atualiza `livros.csv` diretamente no repositório GitHub por meio da API do GitHub, criando um commit. O app recarrega os dados e atualiza os gráficos.

## Arquivos
- `app.py`: aplicativo Streamlit.
- `livros.csv`: base inicial com as colunas `Livro`, `Autor`, `Ano Publicação`, `Nacionalidade Autor`, `Ano Leitura`.
- `requirements.txt`: dependências para a hospedagem.

## 1. Coloque os arquivos no GitHub
Crie um repositório (ou use o seu atual) e envie `app.py`, `livros.csv` e `requirements.txt` para a raiz da branch que pretende publicar, normalmente `main`.

## 2. Crie um token de acesso do GitHub
Crie um Personal Access Token (fine-grained) em GitHub → Settings → Developer settings → Personal access tokens. Dê acesso **somente ao repositório do Atlas** e permissão de repositório **Contents: Read and write**. Não coloque o token no `app.py`, no CSV ou em qualquer arquivo público.

## 3. Publique no Streamlit Community Cloud
1. Acesse https://share.streamlit.io/ e entre com GitHub.
2. Escolha **Create app** e selecione o repositório, branch e `app.py`.
3. Na configuração do app, abra **Advanced settings / Secrets** (ou Manage app → Settings → Secrets, dependendo da interface) e adicione:

```toml
GITHUB_TOKEN = "cole_seu_token_aqui"
GITHUB_REPO = "SEU_USUARIO/SEU_REPOSITORIO"
GITHUB_BRANCH = "main"
CSV_PATH = "livros.csv"
```

Substitua `SEU_USUARIO/SEU_REPOSITORIO` pelo dono e nome reais do repositório. O `CSV_PATH` é o caminho do CSV dentro do repositório.

4. Salve os Secrets e reinicie/reimplante o app, se solicitado.

## 4. Teste com cuidado
1. Abra o app publicado e cadastre um livro de teste.
2. Confirme a mensagem de sucesso.
3. Abra `livros.csv` no GitHub e confira se apareceu um commit com a atualização.
4. Verifique se o livro aparece no Atlas após o recarregamento.

## Como a atualização funciona
- O app lê o CSV atual do GitHub usando a API.
- Ao salvar um livro, verifica duplicata pelo título + autor.
- O app grava o CSV atualizado via API do GitHub; o GitHub cria um commit.
- O app atualiza os gráficos e insights com a base nova.

## Segurança e limitações
- **Nunca publique o token.** Use apenas Streamlit Secrets.
- Use um token limitado ao repositório do Atlas, com `Contents: Read and write`.
- Se várias pessoas cadastrarem ao mesmo tempo, uma gravação pode conflitar; nesse caso, atualize o app e tente novamente.
- O CSV é adequado para uma biblioteca pessoal. Para muitos usuários simultâneos, prefira banco de dados.
- Sem os Secrets, o app abre em modo demonstração/local e não grava no GitHub.
