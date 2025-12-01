# Projeto para a matéria de Base de Dados: Transplante de Órgãos

Este projeto foi desenvolvido para a disciplina de Base de Dados. O sistema gerencia o controle de pacientes (receptores e doadores) e pessoas, utilizando Python para a aplicação e Oracle Database para o armazenamento.

## Pré Requisitos do Sistema

**Sistema operacional:** Windows 10/11 (não foram feitos testes para Linux)

**Python:** 3.10 ou superior (análise da biblioteca Vermin)

**Banco de dados**: Foi utilizado Oracle Database 19c Enterprise Edition Release 19.0.0.0.0 - Production

**Ferramenta SQL:** Foi utilizada a IDE Oracle SQL Developer - Release 24.3.1

## Instalação e Configuração

### Criação da base de dados
Utilizae o **SQL Developer** (ou semelhante) para criar as tabelas e popular o banco:

1. Abra e execute ```SQL/esquema.sql``` (criação das tabelas)
2. Abra e execute ```SQL/dados.sql``` (dados iniciais)

### Instalação das Dependências Python
No console, navegue até a pasta Aplicacao e execute o comando:

```console
    pip install -r requirements.txt
```

### Configuração das Credenciais (.env)
Dentro da pasta Aplicacao, localize o arquivo .env.example

Faça uma cópia e renomeie para .env

Preencha com os dados de conexão (exemplo abaixo):

```bash
    host=localhost
    port=1521
    service_name=xe
    user=seu_usuario_oracle
    password=sua_senha_oracle
```

### Como Executar
Com todas as configurações feitas, execute:

```console
    # Certifique-se de estar dentro da pasta 'Aplicacao'
    python Aplicacao.py
```

## Autores

* Daniel Umeda Kuhn - 13676541

* [Gustavo Curado Ribeiro](https://github.com/GustavoCurado) - 14576732

* [Luís Filipe Silva Forti](https://github.com/LuisFSForti) - 14592348

* [Manoel Thomaz Gama da Silva Neto](https://github.com/thneto1103) - 13676392

* [Pedro Fuziwara Filho](https://github.com/fuzao-jbl) - 13676840