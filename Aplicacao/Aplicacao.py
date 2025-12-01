import oracledb
from tabulate import tabulate
import re
from datetime import datetime
from dotenv import load_dotenv
import os

#======================================= AUXILIAR ======================================

#Converte valores binários para hexadecimais
def BinParaHex(val):
    #Se for binário
    if isinstance(val, bytes):
        #Transforma em hexadecimal
        return val.hex().upper()
    
    #Se não for, retorna sem alterar
    return val

#Função de validação da escrita e dos dígitos verificadores
def VerificaCPF(cpf):
    #Regex, idêntico ao que está no sql
    #r"..." -> string raw, para evitar alertas de erros com '\'
    if not bool(re.match(r"^\d{3}\.\d{3}\.\d{3}\-\d{2}$", cpf)):
        return False
    
    #Para confirmar os digítos verificadores
    #https://www.cadcobol.com.br/calcula_cpf_cnpj_caepf.htm

    #Tira tudo que não for número
    #\d == numeros
    #\D == tudo - \d
    numeros = re.sub(r"\D", "", cpf)
    #Cria uma cópia dos números originais, facilita a leitura
    numerosAux = list(str(numeros))

    #Cálculo do primeiro digíto
    soma = sum(int(numerosAux[i]) * (10 - i) for i in range(0, 9))
    resto11 = soma % 11
    dig1 = 11 - resto11
    if dig1 == 11 or dig1 == 10:
        dig1 = 0

    #Substitui o penúltimo digíto (primeiro dígito verificador) pelo calculado
    numerosAux[-2] = str(dig1)

    #Cálculo do segundo dígito
    soma = sum(int(numerosAux[i]) * (11 - i) for i in range(0, 10))
    resto11 = soma % 11
    dig2 = 11 - resto11
    if dig2 == 11 or dig2 == 10:
        dig2 = 0

    #Compara os digítos encontrados com os passados
    return numeros[-2:] == f"{dig1}{dig2}"

#Função de verificação do estado
def VerificaEstado(estado):
    if estado is None:
        return False

    return estado in {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES",
        "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
        "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
        "SP", "SE", "TO"
    }

def VerificarNumeroResidencia(numero):
    #Se digitou algo, mas não for um número ou for negativo
    if not numero.isdigit():
        return False
    #Se o número tiver mais que 5 digítos, está fora dos limites definidos
    elif int(numero) > 99999:
        return False
    
    return True

#Função para verificar a formatação do telefone
def VerificaTelefone(tel):
    #Regex, idêntico ao que está dentro da base de dados
    #r"..." -> string raw, para evitar alertas de erros com '\'
    return bool(re.match(r"^\(\d{2}\)9\d{4}\-\d{4}$", tel))

#Função para verificar a cor/raça
def VerificaCor(cor):
    if cor is None:
        return False

    #Mesmo conjunto de opções do SQL
    return cor in {
        "BRANCO", "PRETO", "PARDO", "AMARELO", "INDIGENA"
    }

#Função para confirmar a decisão do usuário
def GetConfirmacao(msg):
    confirmacao = None
    while True:
        confirmacao = input(msg + " [S/N]: ").strip().upper()

        if confirmacao in {'N', 'S'}:
            break
        else:
            print("Input inválido!") 

    return confirmacao

#======================================= INSERT ======================================

#Verifica a existência do CPF na base de dados, seja como Pessoa ou como Paciente
#0 == Nenhum Registro, retorna ID nulo
#1 == Registrado em Pessoa, retorna também o ID do registro
#2 == Registrado em Paciente (e, consequentemente, em Pessoa), retorna também o ID do registro
#-1 == Erro, retorna ID nulo
def VerificaExistenciaPessoaPaciente(pool, cpf):
    #Verifica se este CPF já está cadastrado como Pessoa
    #Como Pessoa tem especialização obrigatória, isso só acontecerá com Funcionários

    sqlSelectPessoa = "SELECT * FROM PESSOA WHERE CPF = :cpfPessoa"
    dados = {"cpfPessoa": cpf}

    try:
        #Pega uma conexão com o BD
        with pool.acquire() as conn:
            #Cria um cursor pra conexão
            with conn.cursor() as cursor:
                #cursor.execute trata os dados, protegendo contra injeções
                cursor.execute(sqlSelectPessoa, dados)
                rows = cursor.fetchall()

                #Como o CPF é único, só pode haver 0 ou 1 registro
                if len(rows) == 1:
                    #Pega o seu id de registro
                    idPessoaBytes = rows[0][0]

                    #Verifica se já está registrado como um Paciente
                    sqlSelectPaciente = "SELECT * FROM PACIENTE WHERE PESSOA = :idPessoa"
                    dados = {"idPessoa": idPessoaBytes}
                    #cursor.execute trata os dados, protegendo contra injeções
                    cursor.execute(sqlSelectPaciente, dados)
                    rows = cursor.fetchall()

                    #Novamente, ID é único, terá 0 ou 1 registro
                    if len(rows) == 1:
                        return 2, idPessoaBytes
                    #Se não estiver como Paciente
                    else:
                        return 1, idPessoaBytes
                else:
                    return 0, None
    except oracledb.Error as e:
        print(f"\nErro oracle: {e}\n")
        return -1, None
    except Exception as e:
        print(f"\nErro: {e}\n")
        return -1, None

#Função para pegar os dados para registro em Pessoa
def GetDadosPessoa(pool):
    #Cria fora do loop para serem usados na inserção posteriormente
    cpf = None
    nome = None
    estado = None
    cidade = None
    bairro = None
    rua = None
    numero = None
    telefone1 = None
    telefone2 = None

    print("\n============== Para começar, serão feitas as coletas dos dados como pessoa ==============\n")

    #Loop para o usuário confirmar os dados
    while True:
        #Pega o CPF - Obrigatório
        while True:
            cpf = input("[Obrigatório] Digite o CPF (XXX.XXX.XXX-XX): ").strip()

            if not VerificaCPF(cpf):
                print("CPF inválido!")
            else:
                break

        #Print de separação, para facilitar a legibilidade
        print("")

        #Verifica se o CPF já está no BD
        #Caso a Pessoa exista sem ser Paciente, pega também o ID de registro
        existencia, idPessoaBytes = VerificaExistenciaPessoaPaciente(pool, cpf)
        match existencia:
            #Se teve algum erro
            case -1:
                return
            #Se não estiver
            case 0:
                pass
            #Se estiver como Pessoa
            case 1:
                #Alerta o usuário
                print("O CPF " + cpf + " já está cadastrado como uma pessoa!")

                #Espera por uma decisão
                proceder = GetConfirmacao("Deseja continuar para registrar como paciente?")

                #Se não quiser registrar a Pesoa como Paciente (digitou o CPF errado)
                if proceder == 'N':
                    #Print de separação, para facilitar a legibilidade
                    print("")

                    return None
                #Se quiser, avança pra próxima parte
                else:
                    #Print de separação, para facilitar a legibilidade
                    print("")

                    return {"ID_PESSOA_BYTES": idPessoaBytes}
            #Se estiver como Paciente
            case 2:
                #Informa que já está cadastrado e fecha a operação
                print("O CPF " + cpf + " já está cadastrado como um paciente!")
                
                #Print de separação, para facilitar a legibilidade
                print("")
                return None

        #Se já não estiver cadastrado como Pessoa, pega o restante das informações

        #Pega o nome - Obrigatório
        while True:
            nome = input("[Obrigatório] Digite o nome: ").strip().upper()

            if nome == "":
                print("Nome é obrigatório!")
            elif len(nome) > 50:
                print("Nome deve ter menos que 50 caracteres!")
            else:
                break

        #Print de separação, para facilitar a legibilidade
        print("")

        #Todos os atributos à partir daqui são opcionais

        #Loop para o usuário confirmar se realmente não é para registrar o endereço
        while True:
            #Loop para pegar um estado válido
            while True:
                estado = input("[Opcional] Digite a sigla do estado de residência: ").strip().upper()

                #Se não quiser registrar o estado
                if estado == "":
                    break

                if not VerificaEstado(estado):
                    print("Estado inválido!")
                else:
                    break

            #Endereço só é válido se estiver completo
            #Se qualquer parte faltar, cancela a inserção do endereço

            if estado != "":
                #Loop para pegar uma cidade válida
                while True:
                    cidade = input("[Opcional] Digite a cidade de residência: ").strip().upper()

                    if len(cidade) > 50:
                        print("Nome da cidade deve ter menos que 50 caracteres!")
                    else:
                        break

                if cidade != "":
                    #Loop para pegar um bairro válido
                    while True:
                        bairro = input("[Opcional] Digite o bairro de residência: ").strip().upper()

                        if len(bairro) > 30:
                            print("Nome do bairro deve ter menos que 30 caracteres!")
                        else:
                            break

                    if bairro != "":
                        #Loop para pegar uma rua válida
                        while True:
                            rua = input("[Opcional] Digite a rua de residência: ").strip().upper()

                            if len(rua) > 30:
                                print("Nome da rua deve ter menos que 30 caracteres!")
                            else:
                                break

                        if rua != "":
                            #Loop para pegar um número válido
                            while True:
                                numero = input("[Opcional] Digite o número da residência: ").strip()

                                #Se não quiser registrar o número (e, portanto, o endereço)
                                if numero == "":
                                    #Limpa o número
                                    numero = None
                                    break

                                if not VerificarNumeroResidencia(numero):
                                    print("Número da residência deve ser um inteiro positivo menor que 100000!")
                                else:
                                    numero = int(numero)
                                    break

            #Como o número é o último a ser pego, se ele estiver faltando, o endereço não está completo
            #Limpa o endereço todo
            if numero == None:
                estado = None
                cidade = None
                bairro = None
                rua = None

                print("Endereço não foi digitado por completo, não será registrado!")
                #Espera por uma decisão
                confirmacao = GetConfirmacao("É para pular o endereço?")

                #Se deseja digitar o endereço novamente
                if confirmacao == 'N':
                    #Print de separação, para facilitar a legibilidade
                    print("")
                    continue
            
            #Print de separação, para facilitar a legibilidade
            print("")

            #Se o endereço estiver completo ou foi confirmado que não irá registrá-lo
            break

        #Loop para pegar um telefone válido - Opcional
        while True:
            telefone1 = input("[Opcional] Digite o telefone de contato ((XX)9XXXX-XXXX): ").strip()

            #Se não deseja registrar um telefone, ou apertou [Enter] acidentalmente
            if telefone1 == "":
                confirmacao = GetConfirmacao("Não deseja salvar nenhum telefone de contato?")

                if confirmacao == 'S':
                    #Limpa o telefone
                    telefone1 = None
                    break
                else:
                    continue

            if not VerificaTelefone(telefone1):
                print("Telefone inválido!")
            else:
                break
        
        #Print de separação, para facilitar a legibilidade
        print("")

        #Se não definiu um telefone, não vai definir o outro
        if telefone1 != None:
            #Loop para pegar um telefone válido - Opcional
            while True:
                telefone2 = input("[Opcional] Digite outro telefone de contato ((XX)9XXXX-XXXX): ").strip()

                #Se não deseja registrar um telefone, ou apertou [Enter] acidentalmente
                if telefone2 == "":
                    confirmacao = GetConfirmacao("Não deseja salvar outro telefone de contato?")

                    if confirmacao == 'S':
                        #Limpa o telefone
                        telefone2 = None
                        break
                    else:
                        continue

                if not VerificaTelefone(telefone2):
                    print("Telefone inválido!")
                else:
                    break

        #Print de separação, para facilitar a legibilidade
        print("")

        #Imprime a tabela dos dados coletados
        print("Dados coletados: ")
        print(tabulate(
            [[cpf, nome, estado, cidade, bairro, rua, numero, telefone1, telefone2]], 
            headers=["CPF", "Nome", "Estado", "Cidade", "Bairro", "Rua", "Número", "Telefone de contato 1", "Telefone de contato 2"], 
            tablefmt="psql"))
        
        #Espera por uma decisão
        confirmacao = GetConfirmacao("Dados estão corretos?")

        #Print de separação, para facilitar a legibilidade
        print("")

        #Se os dados estiverem corretos, retorna-os
        if confirmacao == 'S':
            return {
                    "CPF": cpf,
                    "NOME": nome,
                    "ESTADO": estado,
                    "CIDADE": cidade, 
                    "BAIRRO": bairro,
                    "RUA": rua, 
                    "NUMERO": numero, 
                    "TELEFONE1": telefone1, 
                    "TELEFONE2": telefone2
                }

        #Se algum dado estiver incorreto, reinicia o loop
        #Limpa todos os dados
        cpf = None
        nome = None
        estado = None
        cidade = None
        bairro = None
        rua = None
        numero = None
        telefone1 = None
        telefone2 = None

#Função para pegar os dados para registro em Paciente
def GetDadosPaciente():
    #Cria fora do loop para serem usados na inserção posteriormente
    sexo = None
    nascimento = None
    obito = None
    cor = None
    peso = None
    telefoneEmergencia1 = None
    telefoneEmergencia2 = None

    print("\n============== Agora, serão feitas as coletas dos dados como paciente ==============\n")

    #Loop para o usuário confirmar os dados
    while True:
        #Pega o sexo biológico - Obrigatório
        while True:
            sexo = input("[Obrigatório] Digite sexo biológico (M/F): ").strip().upper()

            if sexo not in {"M", "F"}:
                print("Sexo inválido!")
            else:
                break

        #Print de separação, para facilitar a legibilidade
        print("")

        #Pega a data de nascimento - Obrigatória
        while True:
            nascimento = input("[Obrigatório] Digite a data de nascença (Ano-Mês-Dia): ").strip()

            try:
                nascimento = datetime.strptime(nascimento, '%Y-%m-%d')

                if nascimento > datetime.today():
                    print("Data não pode estar no futuro!")
                else:
                    break

            except ValueError:
                print("Data inválida!")

        #Print de separação, para facilitar a legibilidade
        print("")

        #Pega a data e horário de óbito - Opcional
        while True:
            obito = input("[Opcional] Digite a data e horário de óbito (Ano-Mês-Dia Hora:Minuto:Segundo): ").strip()

            if obito == "":
                confirmacao = GetConfirmacao("Paciente ainda está vivo?")

                if confirmacao == 'S':
                    obito = None
                    break
                else:
                    continue

            try:
                obito = datetime.strptime(obito, '%Y-%m-%d %H:%M:%S')

                if obito > datetime.today():
                    print("Data não pode estar no futuro!")
                elif obito < nascimento:
                    print("Não pode ter falecido antes de nascer!")
                else:
                    break

            except ValueError:
                print("Data ou hora inválida!")

        #Print de separação, para facilitar a legibilidade
        print("")

        #Pega a cor/raça do paciente - Obrigatória
        while True:
            cor = input("[Obrigatório] Digite a cor/raça (escreva no masculino): ").strip().upper()

            if not VerificaCor(cor):
                print("Cor/raça inválida!")
            else:
                break

        #Print de separação, para facilitar a legibilidade
        print("")

        #Pega o peso do paciente - Obrigatório
        while True:
            #Como o padrão de sinal decimal no Brasil é a ',', troca por '.'
            peso = input("[Obrigatório] Digite o peso (em kg): ").strip().replace(',', '.')

            try:
                peso = float(peso)
                if peso <= 0:
                    print("Peso deve ser positivo e diferente de 0!")
                elif peso >= 1000:
                    print("Peso deve ser menor que 1000kg!")
                else:
                    break

            except ValueError:
                print("Peso inválido!")

        #Print de separação, para facilitar a legibilidade
        print("")

        #Loop para pegar um telefone de emergência válido - Opcional
        while True:
            telefoneEmergencia1 = input("[Opcional] Digite o telefone de emergência ((XX)9XXXX-XXXX): ").strip()

            #Se não deseja registrar um telefone, ou apertou [Enter] acidentalmente
            if telefoneEmergencia1 == "":
                confirmacao = GetConfirmacao("Não deseja salvar nenhum telefone de emergência?")

                if confirmacao == 'S':
                    #Limpa o telefone
                    telefoneEmergencia1 = None
                    break
                else:
                    continue

            if not VerificaTelefone(telefoneEmergencia1):
                print("Telefone inválido!")
            else:
                break

        #Print de separação, para facilitar a legibilidade
        print("")
        
        #Se não definiu um telefone, não vai definir o outro
        if telefoneEmergencia1 != None:
            #Loop para pegar um telefone válido - Opcional
            while True:
                telefoneEmergencia2 = input("[Opcional] Digite outro telefone de emergência ((XX)9XXXX-XXXX): ")

                #Se não deseja registrar um telefone, ou apertou [Enter] acidentalmente
                if telefoneEmergencia2 == "":
                    confirmacao = GetConfirmacao("Não deseja salvar outro telefone de emergência?")

                    if confirmacao == 'S':
                        #Limpa o telefone
                        telefoneEmergencia2 = None
                        break
                    else:
                        continue

                if not VerificaTelefone(telefoneEmergencia2):
                    print("Telefone inválido!")
                else:
                    break

        #Print de separação, para facilitar a legibilidade
        print("")

        #Imprime a tabela dos dados coletados
        print("Dados coletados: ")
        print(tabulate(
            [[sexo, nascimento, obito, cor, peso, telefoneEmergencia1, telefoneEmergencia2]], 
            headers=["Sexo Biológico", "Data de Nascimento", "Data e Horário de Óbito", "Cor/Raça", 
                     "Peso", "Telefone de Emergência 1", "Telefone de Emergência 2"], 
            tablefmt="psql"))
        
        #Espera por uma decisão
        confirmacao = GetConfirmacao("Dados estão corretos?")

        #Print de separação, para facilitar a legibilidade
        print("")

        #Se os dados estiverem corretos, sai do loop
        if confirmacao == 'S':
            return {
                "SEXO": sexo,
                "NASCIMENTO": nascimento,
                "OBITO": obito,
                "COR": cor,
                "PESO": peso, 
                "TELEFONE_EMERGENCIA1": telefoneEmergencia1, 
                "TELEFONE_EMERGENCIA2": telefoneEmergencia2
            }

        #Se algum dado estiver incorreto, reinicia o loop
        #Limpa todos os dados
        sexo = None
        nascimento = None
        obito = None
        cor = None
        peso = None
        telefoneEmergencia1 = None
        telefoneEmergencia2 = None

#Cuida do processo de inserção do paciente
def InsertPessoaPaciente(pool):
    dadosPessoa = GetDadosPessoa(pool)

    #Se o Paciente já existe, ou se o usuário optou por não registrá-lo
    if dadosPessoa is None:
        return

    dadosPaciente = GetDadosPaciente()
    
    #Após coletar os dados
    try:
        #Pega uma conexão com o BD
        with pool.acquire() as conn:
            #Cria um cursor pra conexão
            with conn.cursor() as cursor:
                idPessoaBytes = dadosPessoa.get("ID_PESSOA_BYTES")
                
                #Se o paciente não estava pré-cadastrado como pessoa
                if idPessoaBytes is None:
                    #Cria no cursor uma variável, necessário pra usar o RETURNING INTO
                    idPessoaRet = cursor.var(oracledb.BINARY)

                    #RETURNING INTO -> pega o ID criado no insert, que vai ser necessário pra próxima parte da inserção
                    sqlInsertPessoa = \
                        "INSERT INTO PESSOA (CPF, NOME, ESTADO, CIDADE, BAIRRO, RUA, NUMERO, TELEFONE1, TELEFONE2) " \
                        "VALUES (:CPF, :NOME, :ESTADO, :CIDADE, :BAIRRO, :RUA, :NUMERO, :TELEFONE1, :TELEFONE2) RETURNING ID INTO :ID_RET"
                    dadosPessoa["ID_RET"] = idPessoaRet

                    #cursor.execute trata os dados, protegendo contra injeções
                    cursor.execute(sqlInsertPessoa, dadosPessoa)
                    #Pega o ID retornado
                    idPessoaBytes = idPessoaRet.getvalue()[0]

                sqlInsertPaciente = \
                    "INSERT INTO PACIENTE (PESSOA, SEXO, NASCIMENTO, OBITO, COR, PESO, TELEFONE_EMERGENCIA1, TELEFONE_EMERGENCIA2) " \
                    "VALUES (:ID_PESSOA_BYTES, :SEXO, :NASCIMENTO, :OBITO, :COR, :PESO, :TELEFONE_EMERGENCIA1, :TELEFONE_EMERGENCIA2)"
                
                dadosPaciente["ID_PESSOA_BYTES"] = idPessoaBytes

                #cursor.execute trata os dados, protegendo contra injeções
                cursor.execute(sqlInsertPaciente, dadosPaciente)
                #Chama commit na base de dados, salvando os dados por definitivo
                conn.commit()

                print(f"\n\nPaciente ID = {BinParaHex(idPessoaBytes)} registrado com sucesso!")
                #Instrui o usuário à orientar o Paciente
                print("Caso o paciente tenha interesse em se tornar doador de órgãos, informe-o sobre os próximos passos:")
                print("- Ele pode manifestar sua vontade conversando com a família, que é a responsável pela autorização final.")
                print("- É recomendado esclarecer dúvidas com a equipe médica ou com o serviço de orientação do hospital.")
                print("- Se desejar, o paciente pode solicitar materiais explicativos sobre doação de órgãos.")
                print("- Reforce que a decisão é voluntária e pode ser alterada a qualquer momento.\n\n")
    
    #with conn -> realiza rollback automático quando sai do seu bloco
    except oracledb.Error as e:
        print(f"\nErro oracle: {e}\n")
    except Exception as e:
        print(f"\nErro: {e}\n")

#======================================= SELECT ======================================

def SelectPessoa(pool):
    idPessoa = None
    cpf = None
    nome = None
    estado = None
    cidade = None
    bairro = None
    rua = None
    numero = None
    telefone1 = None
    telefone2 = None

    print("Para desprezar a coluna (ou seja, não usá-la como filtro), apenas pressione [Enter]")

    #Não há necessidade de verificar os dados, não é um registro permanente que deve estar perfeito

    idPessoa = input("Digite o ID da pessoa (hexadecimal de até 16 caracteres): ").strip().upper() or None
    cpf = input("Digite o CPF da pessoa (XXX.XXX.XXX-XX): ").strip().upper() or None
    nome = input("Digite o nome da pessoa: ").strip().upper() or None
    estado = input("Digite a sigla do estado de residência da pessoa: ").strip().upper() or None
    cidade = input("Digite a cidade de residência da pessoa: ").strip().upper() or None
    bairro = input("Digite o bairro de residência da pessoa: ").strip().upper() or None
    rua = input("Digite a rua de residência da pessoa: ").strip().upper() or None
    numeroStr = input("Digite o número de residência da pessoa: ").strip()
    if numeroStr != "":
        try:
            numero = int(numeroStr)
        except ValueError:
            print("Número digitado inválido! Informação será descartada.")
            #Limpa o numero, por garantia
            numero = None

    telefone1 = input("Digite o primeiro telefone de contato ((XX)9XXXX-XXXX): ").strip() or None
    telefone2 = input("Digite o segundo telefone de contato ((XX)9XXXX-XXXX): ").strip() or None

    #Todos os valores que estiverem como None serão ignorados pelo trecho ":atributo IS NULL"
    sqlSelectPessoa = "SELECT * FROM PESSOA WHERE " \
            "(:idPessoa IS NULL OR ID = :idPessoa) " \
        "AND (:cpf IS NULL OR CPF = :cpf) " \
        "AND (:nome IS NULL OR NOME LIKE '%' || :nome || '%') " \
        "AND (:estado IS NULL OR ESTADO = :estado) " \
        "AND (:cidade IS NULL OR CIDADE = :cidade) " \
        "AND (:bairro IS NULL OR BAIRRO = :bairro) " \
        "AND (:rua IS NULL OR RUA = :rua) " \
        "AND (:numero IS NULL OR NUMERO = :numero) " \
        "AND (:telefone1 IS NULL OR TELEFONE1 = :telefone1) " \
        "AND (:telefone2 IS NULL OR TELEFONE2 = :telefone2)"

    dados = {
        "idPessoa": idPessoa,
        "cpf": cpf,
        "nome": nome,
        "estado": estado,
        "cidade": cidade,
        "bairro": bairro,
        "rua": rua,
        "numero": numero,
        "telefone1": telefone1,
        "telefone2": telefone2
    }

    try:
        #Pega uma conexão com o BD
        with pool.acquire() as conn:
            #Cria um cursor pra conexão
            with conn.cursor() as cursor:
                #cursor.execute trata os dados, protegendo contra injeções
                cursor.execute(sqlSelectPessoa, dados)

                rows = cursor.fetchall()
                #Pega o nome das colunas
                cols = [desc[0] for desc in cursor.description]

                #Converte a primeira coluna de toda linha (o ID) de binário para hexadecimal
                #[...] + row[1:] -> concatena o resultado da função com o restante da linha
                hexRows = [[BinParaHex(row[0])] + list(row[1:]) for row in rows]

                #Imprime a tabela obtida
                print(f"\n==== Tabela Pessoa ====")
                print(tabulate(hexRows, headers=cols, tablefmt="psql"))

                #Print de separação, para facilitar a legibilidade
                print("")

    except oracledb.Error as e:
        print(f"\nErro oracle: {e}\n")
    except Exception as e:
        print(f"\nErro: {e}\n")

#======================================= MAIN ======================================

if __name__ == "__main__":
    #Abre o .env
    load_dotenv()

    #Pega os dados do .env
    db_user = os.getenv("user")
    db_pass = os.getenv("password")
    db_host = os.getenv("host")
    db_port = os.getenv("port")
    db_service = os.getenv("service_name")

    #Se algum dado estiver faltando (ou o .env em si)
    if not all([db_user, db_pass, db_host, db_port, db_service]):
        print("\n[ERRO] Arquivo .env incompleto!\n")
        print("Verifique: user, password, host, port, service_name\n")
        exit()

    dsn = oracledb.makedsn(host=db_host, port=db_port, service_name=db_service)

    pool = None
    try:
        print("Conectando ao banco de dados...")
        pool = oracledb.create_pool(
            user=db_user,
            password=db_pass,
            dsn=dsn,
            min=1,
            max=2,
            increment=1
        )
        print("Sistema iniciado com sucesso!\n")

        while True:
            print(
                "Selecione uma função:\n" +
                "[0] Inserir um novo paciente\n" +
                "[1] Procurar uma pessoa\n" +
                "[2] Fechar o programa\n"
            )

            comando = input("Digite a função desejada: ").strip()

            match comando:
                case '0':
                    InsertPessoaPaciente(pool)
                case '1':
                    SelectPessoa(pool)
                case '2':
                    print("\nEncerrando o código...")
                    break
                case _:
                    print("Comando inválido!\n")

    except oracledb.Error as e:
        print(f"\n[ERRO FATAL DE CONEXÃO]: {e}")
    except KeyboardInterrupt:
        print("\n\nEncerrando forçadamente pelo usuário...")
    #Independentemente do erro esse trecho irá rodar, até mesmo se não ocorrer (comando '2')
    finally:
        if pool is not None:
            pool.close()
            print("Conexão com o banco encerrada.\n")