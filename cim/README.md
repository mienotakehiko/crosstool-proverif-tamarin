# Common Iterative Model sources

A Common Iterative Model (CIM) describes one protocol with iterated state as a TOML file. The generator [`cimc`](../cimc/) compiles a CIM into four ProVerif encodings and four Tamarin variants.

| Path | Content |
| --- | --- |
| [`signers/lmots.toml`](signers/lmots.toml) | LM-OTS signer with digits of two bits, one message chain and one checksum chain |
| [`signers/lms_s2.toml`](signers/lms_s2.toml) | LMS signer with two leaves over that LM-OTS signer |
| [`kudos/`](kudos/) | Specifications of the twelve finite KUDOS schedules of series K and the generators that print their ProVerif and Tamarin models |

The two signer files are the inputs of series G, of the mutation series M and V4 and of the regeneration checks. The inputs of the validation series V1 and V2 live with their records under [`validation/`](../validation/).

The directory `kudos/RB1/` holds one specification for two schedules. The table [`runs/K/specification-index.tsv`](../runs/K/specification-index.tsv) names the specification and the generator of every schedule, and `python3 -B scripts/check_kudos_models.py` regenerates all 24 model inputs and compares them with the archived inputs.
