"""Studio — la porte d'entrée de la chaîne pour quelqu'un qui n'ouvre pas de terminal.

Trois modules, dans cet ordre de dépendance :

    jobs.py     ce qu'est une production, et comment lire son avancement
                sur le disque. Aucun effet de bord, aucun réseau.
    runner.py   la file d'attente d'un poste : un seul travail à la fois,
                lancé comme sous-processus, repris après un redémarrage.
    server.py   le HTTP : dépôt du support, avancement, et le site lui-même.

Le studio ne refait pas le travail de la chaîne : il lance la même commande
que celle documentée, `s2m-course-pdf`, et lit les fichiers qu'elle écrit.
"""
