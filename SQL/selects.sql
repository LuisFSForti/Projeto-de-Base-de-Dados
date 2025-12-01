--Procura todos os doadores disponíveis para os receptores com prioridade máxima,
--avaliando o tipo sanguíneo encontrado nos exames de cada um para verificar a compatibilidade do receptor com o doador.
--Se um deles não tiver realizado o exame, eles não serão considerados pela bsuca
SELECT DISTINCT R.TIPO_ORGAO, R.RECEPTOR, D.DOADOR
FROM RECEPTOR_ESPERA R 
JOIN EXAME E1 ON R.RECEPTOR = E1.PACIENTE
JOIN DOADOR_DOA D ON R.TIPO_ORGAO = D.TIPO_ORGAO
JOIN EXAME E2 ON D.DOADOR = E2.PACIENTE
WHERE
--Verifica se os tipos sanguíneos são compatíveis
(
        --Receptor == O
        --Doador == O
        (E1.RESULTADO LIKE '% O_,%'
         AND E2.RESULTADO LIKE '% O_,%')

        --Receptor == A
        --Doador == O ou A
    OR  (E1.RESULTADO LIKE '% A_,%'
         AND (
                E2.RESULTADO LIKE '% O_,%'
             OR E2.RESULTADO LIKE '% A_,%'
             )
        )

    --Receptor == B
    --Doador == O ou B
    OR  (E1.RESULTADO LIKE '% B_,%'
         AND (
                E2.RESULTADO LIKE '% O_,%'
             OR E2.RESULTADO LIKE '% B_,%'
             )
        )

    --Receptor == O
    --Doador == O ou A ou B ou AB
    OR  (E1.RESULTADO LIKE '% AB_,%'
         AND (
                E2.RESULTADO LIKE '% O_,%'
             OR E2.RESULTADO LIKE '% A_,%'
             OR E2.RESULTADO LIKE '% B_,%'
             OR E2.RESULTADO LIKE '% AB_,%'
             )
        )
)
AND
    --Compara o Rh
    NOT (E1.RESULTADO LIKE '%-,%' AND E2.RESULTADO LIKE '%+,%')
    --Verifica se o receptor tem prioridade máxima
AND R.PRIORIDADE = 1;


--Lista o número de óbitos durante cirurgias de cada hospital
SELECT H.NOME,
--Conta o número de pessoas cujo horário de óbito 
--está dentro da janela de alguma cirurgia em que elas eram pacientes
COUNT(
    CASE
        WHEN P.OBITO BETWEEN C.DATA_HORARIO_INICIO AND C.DATA_HORARIO_TERMINO 
        THEN 1
    END
) AS OBITOS
FROM HOSPITAL H
LEFT JOIN CIRURGIA C ON H.ID = C.HOSPITAL         --LEFT JOIN para preservar, no select, hospitais que não realizaram cirurgia alguma
LEFT JOIN PACIENTE P ON P.PESSOA = C.PACIENTE
GROUP BY H.NOME
ORDER BY OBITOS DESC;


-- Lista os doadores que doaram todos os órgãos possíveis
-- Esse é o nosso SELECT que utiliza divisão relacional
SELECT DISTINCT C.PACIENTE
FROM CIRURGIA C
WHERE NOT EXISTS
(
    (
        SELECT T.NOME
        FROM TIPO_ORGAO T
    )
    MINUS
    (
        SELECT O.TIPO
        FROM CIRURGIA C2 JOIN ORGAO O
        ON C2.ID = O.COLETA
        WHERE C2.PACIENTE = C.PACIENTE
    )
);

--Checa se existem pessoas que doaram órgãos que elas receberam em uma cirurgia anterior. Os rins são desconsiderados nessa busca
SELECT C.PACIENTE, O.TIPO, O.LADO
FROM CIRURGIA C JOIN ORGAO O
ON C.ID = O.COLETA
JOIN ORGAO O2
ON O2.TIPO = O.TIPO AND O2.LADO = O.LADO
JOIN CIRURGIA C2
ON C2.ID = O2.RECEPCAO
AND C2.PACIENTE = C.PACIENTE 
WHERE C.DATA_HORARIO_INICIO > C2.DATA_HORARIO_TERMINO
AND O.TIPO <> 'RIM';


--Seleciona hospitais que realizaram cirurgias para os quais não estavam autorizados
SELECT H.NOME, O.TIPO, TO_CHAR(C.DATA_HORARIO_INICIO, 'YYYY/MM/DD HH24:MI:SS') AS DATA_HORARIO_INICIO, C.TIPO
FROM HOSPITAL H 
JOIN CIRURGIA C ON C.HOSPITAL = H.ID
JOIN ORGAO O ON C.ID = O.COLETA OR C.ID = O.RECEPCAO
LEFT JOIN AUTORIZACAO_HOSPITAL A ON H.ID = A.HOSPITAL
AND INSTR(A.AUTORIZACAO_SNT, O.TIPO) > 0
AND C.DATA_HORARIO_INICIO < A.VALIDADE_AUTORIZACAO
WHERE A.HOSPITAL IS NULL;

--Nota: pode acontecer que um hospital realize uma cirurgia não autorizada, mas renove sua autorização depois
--Nesse caso, a informação de que a cirurgia foi realizada indevidamente será perdida da base de dados