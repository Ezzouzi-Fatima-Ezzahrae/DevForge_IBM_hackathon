# DevForge — Impact (chiffres mesurés uniquement)

Méthodologie : uniquement les runs de pipeline réels (project_id `proj_*`), les
project_id `test_*` et `other_*` sont des fixtures de tests unitaires et sont exclus.

## Runs réels mesurés
3 runs complets à ce jour : `proj_cbc6df34`, `proj_a36ecb5c`, `proj_251eb3b5`.

## Résultats
| Mesure | Valeur |
|---|---|
| Runs terminés (RELEASED) | 3 / 3 |
| Bugs détectés par les tests puis corrigés par l'agent de debug réel | 3 (1 par run, ownership check) |
| Tests avant fix | 17/20 (à chaque run) |
| Tests après fix | 20/20 (à chaque run) |
| Failles de sécurité détectées et bloquées par l'agent de sécurité réel | 3 (1 par run, haute sévérité) |
| Retries utilisés | 2 par run (1 test, 1 sécurité) |

## Limites à ne pas cacher
- L'agent de plan rejoue le même plan sauvegardé pour toute idée soumise (pas encore adaptatif).
- La correction de la faille de sécurité utilise un agent stub, pas un vrai fix agent — donc "détecté et bloqué" est mesuré, "corrigé automatiquement" pour la sécurité ne l'est pas.
- 3 runs seulement : échantillon petit, tous avec la même idée de démo.
