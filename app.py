import base64
import io
import os
import re
from collections import Counter
from datetime import date

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Atlas de Leituras", page_icon="📚", layout="wide")

REQUIRED_COLUMNS = ["Livro", "Autor", "Ano Publicação", "Nacionalidade Autor", "Ano Leitura"]
GITHUB_API = "https://api.github.com"

COUNTRY_PT = {
    "United States": "Estados Unidos", "United States of America": "Estados Unidos",
    "United Kingdom": "Reino Unido", "South Korea": "Coreia do Sul", "North Korea": "Coreia do Norte",
    "New Zealand": "Nova Zelândia", "South Africa": "África do Sul", "Saudi Arabia": "Arábia Saudita",
    "United Arab Emirates": "Emirados Árabes Unidos", "Czech Republic": "República Tcheca",
    "Czechia": "República Tcheca", "Netherlands": "Países Baixos", "The Netherlands": "Países Baixos",
    "Ivory Coast": "Costa do Marfim", "Democratic Republic of the Congo": "República Democrática do Congo",
    "Republic of the Congo": "República do Congo", "Dominican Republic": "República Dominicana",
    "Russia": "Rússia", "Germany": "Alemanha", "France": "França", "Spain": "Espanha",
    "Italy": "Itália", "Brazil": "Brasil", "Japan": "Japão", "China": "China", "India": "Índia",
    "Canada": "Canadá", "Mexico": "México", "Norway": "Noruega", "Sweden": "Suécia",
    "Denmark": "Dinamarca", "Finland": "Finlândia", "Ireland": "Irlanda", "Iceland": "Islândia",
    "Portugal": "Portugal", "Greece": "Grécia", "Turkey": "Turquia", "Türkiye": "Turquia",
    "Iran": "Irã", "Iraq": "Iraque", "Egypt": "Egito", "Morocco": "Marrocos",
    "Nigeria": "Nigéria", "Kenya": "Quênia", "Australia": "Austrália", "Austria": "Áustria",
    "Belgium": "Bélgica", "Switzerland": "Suíça", "Poland": "Polônia", "Ukraine": "Ucrânia",
    "Romania": "Romênia", "Hungary": "Hungria", "Pakistan": "Paquistão", "Vietnam": "Vietnã",
    "Indonesia": "Indonésia", "Philippines": "Filipinas", "Taiwan": "Taiwan", "Argentina": "Argentina",
    "Chile": "Chile", "Colombia": "Colômbia", "Scotland": "Escócia", "Wales": "País de Gales",
    "England": "Inglaterra", "Unknown": "Não informado", "": "Não informado"
}

def country_pt(name):
    return COUNTRY_PT.get(str(name), str(name))

def norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())

def get_config():
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo = st.secrets.get("GITHUB_REPO", "")
        branch = st.secrets.get("GITHUB_BRANCH", "main")
        csv_path = st.secrets.get("CSV_PATH", "livros.csv")
    except Exception:
        token, repo, branch, csv_path = "", "", "main", "livros.csv"
    return str(token).strip(), str(repo).strip(), str(branch).strip() or "main", str(csv_path).strip() or "livros.csv"

TOKEN, REPO, BRANCH, CSV_PATH = get_config()

def github_headers():
    return {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}

def github_get_csv():
    if not (TOKEN and REPO):
        return None, None
    url = f"{GITHUB_API}/repos/{REPO}/contents/{CSV_PATH}"
    response = requests.get(url, headers=github_headers(), params={"ref": BRANCH}, timeout=20)
    if response.status_code == 404:
        raise RuntimeError(f"Não encontrei `{CSV_PATH}` no repositório `{REPO}` (branch `{BRANCH}`).")
    response.raise_for_status()
    payload = response.json()
    content = base64.b64decode(payload["content"]).decode("utf-8-sig")
    return pd.read_csv(io.StringIO(content)), payload.get("sha")

def github_put_csv(df, sha):
    if not (TOKEN and REPO):
        raise RuntimeError("Configure GITHUB_TOKEN e GITHUB_REPO nos Secrets do Streamlit.")
    csv_bytes = df[REQUIRED_COLUMNS].to_csv(index=False, encoding="utf-8-sig").encode("utf-8")
    url = f"{GITHUB_API}/repos/{REPO}/contents/{CSV_PATH}"
    content = base64.b64encode(csv_bytes).decode("ascii")
    body = {"message": "Atualiza livros.csv pelo Atlas de Leituras",
            "content": content, "branch": BRANCH}
    if sha:
        body["sha"] = sha
    response = requests.put(url, headers=github_headers(), json=body, timeout=30)
    if response.status_code == 409 or response.status_code == 422:
        raise RuntimeError("O CSV mudou no GitHub durante o cadastro. Atualize o app e tente novamente.")
    if response.status_code in (401, 403):
        raise RuntimeError("O GitHub recusou a gravação. Confira o token e a permissão Contents: Read and write.")
    response.raise_for_status()
    return response.json()

def clean_df(df):
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[REQUIRED_COLUMNS].copy()
    for col in ["Livro", "Autor", "Nacionalidade Autor"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    for col in ["Ano Publicação", "Ano Leitura"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["Nacionalidade Autor"] = df["Nacionalidade Autor"].replace({
        "Soth Korea": "South Korea", "South korea": "South Korea", "nan": "Unknown", "": "Unknown"
    })
    return df

@st.cache_data(ttl=30, show_spinner=False)
def read_local_csv(path):
    return pd.read_csv(path, encoding="utf-8-sig")

def load_data():
    if TOKEN and REPO:
        df, sha = github_get_csv()
        return clean_df(df), sha, "GitHub"
    local_path = os.path.join(os.path.dirname(__file__), CSV_PATH)
    if os.path.exists(local_path):
        return clean_df(read_local_csv(local_path)), None, "arquivo local (modo demonstração)"
    return clean_df(pd.DataFrame(columns=REQUIRED_COLUMNS)), None, "sem fonte configurada"

st.markdown("""
<style>
:root { --ink:#242a26; }
.block-container {padding-top:2rem; padding-bottom:3rem; max-width:1300px}
h1,h2,h3 {letter-spacing:-.02em}
[data-testid="stMetric"] {background:#fffefa;border:1px solid #e4e5dc;padding:16px;border-radius:16px}
div[data-testid="stForm"] {background:#fffefa;border:1px solid #e4e5dc;padding:18px;border-radius:18px}
</style>
""", unsafe_allow_html=True)

st.title("📚 Atlas de Leituras")
st.caption("Sua biblioteca por ano de leitura e nacionalidade dos autores. Cadastros podem ser gravados diretamente no CSV do GitHub.")

try:
    df, file_sha, data_source = load_data()
except Exception as exc:
    st.error(f"Não consegui carregar os dados do GitHub: {exc}")
    st.stop()

if data_source != "GitHub":
    st.warning("O app está em modo local/demonstração. Para salvar os cadastros diretamente no GitHub, configure os Secrets conforme o README.")
else:
    st.success(f"Dados carregados de `{REPO}/{CSV_PATH}` na branch `{BRANCH}`. Novos livros serão salvos no GitHub.")

with st.expander("➕ Adicionar um livro", expanded=False):
    with st.form("add_book_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        title = c1.text_input("Livro *")
        author = c2.text_input("Autor *")
        pubyear = c1.number_input("Ano de publicação", min_value=0, max_value=2100, value=0, step=1, help="Deixe 0 se não souber.")
        nationality = c2.text_input("Nacionalidade do autor (em inglês) *", placeholder="Ex.: Brazil")
        readyear = c1.number_input("Ano de leitura *", min_value=1900, max_value=2100, value=date.today().year, step=1)
        submitted = st.form_submit_button("Salvar livro", type="primary", use_container_width=True)
    if submitted:
        if not title.strip() or not author.strip() or not nationality.strip():
            st.error("Preencha Livro, Autor e Nacionalidade.")
        elif ((df["Livro"].map(norm) == norm(title)) & (df["Autor"].map(norm) == norm(author))).any():
            st.error("Esse título e autor já existem na lista. Verifique antes de cadastrar novamente.")
        elif data_source != "GitHub":
            st.error("Para salvar permanentemente no GitHub, configure os Secrets primeiro. Veja as instruções no README.")
        else:
            new_row = pd.DataFrame([{
                "Livro": title.strip(), "Autor": author.strip(),
                "Ano Publicação": int(pubyear) if pubyear else pd.NA,
                "Nacionalidade Autor": nationality.strip(), "Ano Leitura": int(readyear)
            }])
            updated = pd.concat([df, new_row], ignore_index=True)
            try:
                with st.spinner("Salvando o livro no GitHub…"):
                    github_put_csv(clean_df(updated), file_sha)
                st.cache_data.clear()
                st.success("Livro adicionado! O CSV do GitHub foi atualizado com um commit.")
                st.rerun()
            except Exception as exc:
                st.error(f"Não foi possível salvar: {exc}")

st.divider()
filter_col, search_col = st.columns([1, 2])
years = sorted([int(y) for y in df["Ano Leitura"].dropna().unique()], reverse=True)
with filter_col:
    year_options = ["Todos os anos"] + years
    selected_year = st.selectbox("Filtrar por ano de leitura", year_options)
with search_col:
    search = st.text_input("Buscar livro ou autor", placeholder="Digite um título ou nome")
filtered = df.copy()
if selected_year != "Todos os anos":
    filtered = filtered[filtered["Ano Leitura"] == selected_year]
if search.strip():
    mask = (filtered["Livro"].str.contains(search, case=False, na=False, regex=False) |
            filtered["Autor"].str.contains(search, case=False, na=False, regex=False))
    filtered = filtered[mask]

counts = filtered[filtered["Nacionalidade Autor"].ne("Unknown")].groupby("Nacionalidade Autor").size().sort_values(ascending=False)
authors = filtered.groupby("Autor").size().sort_values(ascending=False)
top_country = counts.index[0] if len(counts) else "—"
top_author = authors.index[0] if len(authors) else "—"
distinct_countries = filtered.loc[filtered["Nacionalidade Autor"].ne("Unknown"), "Nacionalidade Autor"].nunique()
m1,m2,m3,m4 = st.columns(4)
m1.metric("Livros no filtro", len(filtered))
m2.metric("Nacionalidades", int(distinct_countries))
m3.metric("Autor mais frequente", top_author)
m4.metric("País mais representado", country_pt(top_country))

st.subheader("🌍 Mapa-múndi literário")
st.caption("A cor indica a quantidade de livros por nacionalidade. Passe o cursor ou toque em um país para explorar os dados.")
try:
    import pycountry
    def iso3(name):
        aliases = {"United States":"USA", "South Korea":"KOR", "North Korea":"PRK",
                   "Russia":"RUS", "Turkey":"TUR", "Czech Republic":"CZE",
                   "Vietnam":"VNM", "Iran":"IRN", "Syria":"SYR", "Bolivia":"BOL",
                   "Tanzania":"TZA", "Venezuela":"VEN", "Moldova":"MDA",
                   "Laos":"LAO", "Soth Korea":"KOR"}
        if name in aliases:
            return aliases[name]
        try:
            return pycountry.countries.lookup(name).alpha_3
        except LookupError:
            return None
    map_df = counts.rename_axis("country").reset_index(name="books")
    map_df["iso3"] = map_df["country"].map(iso3)
    map_df["country_pt"] = map_df["country"].map(country_pt)
    map_df = map_df.dropna(subset=["iso3"])
    if not map_df.empty:
        fig_map = px.choropleth(map_df, locations="iso3", color="books", hover_name="country_pt",
                                hover_data={"books": True, "iso3": False, "country": False, "country_pt": False},
                                color_continuous_scale=["#f5d7c7", "#d9825b", "#8c3e27"],
                                projection="natural earth", labels={"books":"Livros"})
        fig_map.update_geos(showframe=False, showcoastlines=True, coastlinecolor="#ffffff",
                            showland=True, landcolor="#f0eee8", showcountries=True,
                            countrycolor="#ffffff", showocean=True, oceancolor="#ffffff",
                            bgcolor="#ffffff", lataxis_range=[-58,85])
        fig_map.update_layout(height=500, margin=dict(l=0,r=0,t=10,b=0),
                              paper_bgcolor="#fffefa", plot_bgcolor="#fffefa",
                              coloraxis_colorbar=dict(title="Livros"))
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("Ainda não há nacionalidades reconhecidas para desenhar no mapa.")
except Exception:
    st.info("O mapa não pôde ser desenhado. As demais visualizações continuam disponíveis.")

left, right = st.columns(2)
with left:
    st.subheader("📊 Nacionalidades mais presentes")
    if not counts.empty:
        chart_df = counts.head(15).rename_axis("Nacionalidade").reset_index(name="Livros")
        chart_df["Nacionalidade"] = chart_df["Nacionalidade"].map(country_pt)
        fig = px.bar(chart_df.sort_values("Livros"), x="Livros", y="Nacionalidade", orientation="h",
                     color_discrete_sequence=["#c66c46"], text="Livros")
        fig.update_layout(height=460, margin=dict(l=0,r=10,t=10,b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para esse filtro.")

with right:
    st.subheader("📚 Décadas de publicação")
    decades = filtered.dropna(subset=["Ano Publicação"]).copy()
    if not decades.empty:
        decades["Década"] = (decades["Ano Publicação"].astype(int)//10*10).astype(str) + "s"
        decade_counts = decades.groupby("Década").size().sort_index()
        dec_df = decade_counts.rename_axis("Década").reset_index(name="Livros")
        fig = px.bar(dec_df, x="Década", y="Livros", color_discrete_sequence=["#78917e"], text="Livros")
        fig.update_layout(height=460, margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem anos de publicação disponíveis.")

st.subheader("✨ Descobertas sobre autores")
if len(filtered):
    author_counts = filtered.groupby("Autor").size().sort_values(ascending=False)
    a1,a2,a3 = st.columns(3)
    a1.metric("Autor com mais livros", author_counts.index[0], int(author_counts.iloc[0]))
    a2.metric("Autores distintos", filtered["Autor"].nunique())
    a3.metric("Autores com mais de um livro", int((author_counts > 1).sum()))
    author_pick = st.selectbox("Explorar autor", sorted(filtered["Autor"].dropna().unique()), key="author_pick")
    author_books = filtered[filtered["Autor"] == author_pick]
    nationality = author_books["Nacionalidade Autor"].replace("Unknown", pd.NA).dropna()
    st.markdown(f"**{author_pick}**")
    st.write(f"Nacionalidade registrada: {country_pt(nationality.iloc[0]) if len(nationality) else 'Não informada'}")
    st.write(f"Livros no filtro: {len(author_books)} · Anos de leitura: {', '.join(map(str, sorted(author_books['Ano Leitura'].dropna().unique()))) or 'não informados'}")
    st.dataframe(author_books[["Livro","Ano Publicação","Ano Leitura"]].sort_values("Ano Leitura", na_position="last"), use_container_width=True, hide_index=True)
else:
    st.info("Nenhum livro no filtro atual.")

st.subheader("🗺️ Descobertas sobre países")
if len(counts):
    country_pick = st.selectbox("Explorar país/nacionalidade", [c for c in counts.index], format_func=country_pt, key="country_pick")
    country_books = filtered[filtered["Nacionalidade Autor"] == country_pick]
    author_count_country = country_books.groupby("Autor").size().sort_values(ascending=False)
    p1,p2,p3 = st.columns(3)
    p1.metric("Livros associados", len(country_books))
    p2.metric("Autores distintos", country_books["Autor"].nunique())
    p3.metric("Autor principal", author_count_country.index[0] if len(author_count_country) else "—",
              int(author_count_country.iloc[0]) if len(author_count_country) else 0)
    st.write("**Livros associados e autores:**")
    st.dataframe(country_books[["Livro","Autor","Ano Publicação","Ano Leitura"]].sort_values("Ano Leitura", na_position="last"),
                 use_container_width=True, hide_index=True)
else:
    st.info("Não há países identificados no filtro.")

with st.expander("📖 Ver tabela completa / exportar dados"):
    st.dataframe(filtered[REQUIRED_COLUMNS].sort_values(["Ano Leitura","Autor"], na_position="last"),
                 use_container_width=True, hide_index=True)
    csv_download = filtered[REQUIRED_COLUMNS].to_csv(index=False, encoding="utf-8-sig").encode("utf-8")
    st.download_button("Baixar CSV do filtro", csv_download, file_name="livros_filtrados.csv", mime="text/csv")

st.caption(f"Fonte dos dados: {data_source}. Total na base: {len(df)} livros.")
