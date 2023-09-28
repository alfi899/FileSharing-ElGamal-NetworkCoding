# BachelorProjekt

Peer to Peer File Sharing mit Netzwerkodierung auf basis von Elgamal Verschlüsselung

# Peer to Peer:
    Bei start des Programms muss ein Port angegeben werden, an den sich der Peer verbinden soll.
    Ist ein Peer der erste Peer in dem Netzwerk, muss kein Port angegeben werden. Dieser bekommt
    dann automatisch die Addresse "5000". 
    Jeder weitere Peer der das Netzwerk betretet möchte, muss nun eine Addresse mit angeben (z.B. 5000)
    um sich mit dem ersten Peer zu verbinden.
    Für jeden weiteren Peer wird dessen Addresse in der Commando Zeile angezeigt, sodass weiter Peers diese 
    Addresse nutzen können um sich mit diesem Peer zu verbinden.
    So kann ein P2P Netzwerk aufgebaut werden, um den prozess des Netzwork Codings besser zu veranschaulichen


# File Sharing:
    Jeder Node kann eine File auswählen, welche er über das Netzwerk an alle anderen Versenden möchte.
    Die Datei wird in einzelne (gleichgroße) Packete unterteilt und diese in einer Liste zwischengespeichert.
    Danach werden die einzelnen Packete mit der Elgamal Verschlüsselung verschlüsselt und der Schlüssel für jedes Packet wird in einer weiteren Liste 
    zwischengespeichert.
    
    Kombinationen werden erstellt, indem die einzelnen Packete mit jeweils zufälligen
    Zahlen exponentiert und miteinander multipliziert werden.

        (c1,c2)^a * (c1,c2)^b * ....

    Jede einzelne combination wird mit den exponenten versendet. Sobal ein Node genügend
    combinationen und exponenten hat, kann dieser die Zahlen entschlüsseln und die 
    Datei wider herstellen.

    Hierzu werden die empfangen Kombinationen durch ElGamal Entschlüsselt (x1,x2,..,xn), und diese mit der modularen inversen matrix der Exponenten multipliziert und exponentiert.

        B = A^-1 % q          m1 = x1**B[0][0] * x2**B[0][1] * ... * xn**B[0][n]
                              m2 = x1**B[1][0] * x2**B[1][1] * ... * xn**B[1][n]
                                        .....         .....           .....
                              mn = x1**B[n][0] * x2**B[n][1] * ... * xn**B[n][n]

    Hierdurch werden die Uhrsprünglichen Nachrichten wieder berechnet und wir byte Werte 
    davon werden wieder in eine neue Datei geschrieben.


# Netzwerkodierung:
    Ist ein Node kein intermediade Node (also bekommt nur Packete von einem weiteren Node) versendet dieser die Packete
    einfach direkt weiter.
    Ist ein Node ein intemediade, erstellt dieser lineare combinationen von den empfangenen Packeten und sended diese stattdessen
    weiter.
    Ein Node welcher nun genügend lineare kombination hat, kann die ursprünglichen Nachrichten wieder herstellen

# Installation
    Clone das Repository:
        git clone ...

    Öffne eine Kommandozeile und starte den ersten Peer im Netzwerk
        python3 app.py

    Starte in weiteren Kommandozeilen beliebig viele Nodes mit dem Befehl.:
        python3 app.py [Port to connect to]
        python3 app.py 5000


# Anmerkungen
    > Wenn das GUI window geschlossen wird, läuft das Programm im Hintergrund noch weiter
    > Da nur lokal getestet, läuft alles über '127.0.0.1', daher ist auch nur ein Port für die 
      Verbindung notwendig