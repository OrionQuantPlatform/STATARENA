# Saved player positions

The archived field census and the saved-resource sample have different data coverage. The saved RDS resource /matches/m_00OYeh/players/p_1BvJC3 contains top-level position_id 33 and nested player.position_id null. The existing single-player writer rejects the top-level field. Source SHA-256 is c45b7feb9fbee0074eb1015fc5474b91497d79aaf9bdf55ed5cca3bab4613029. Use the retained offline capture; no further RDS reads.

Expect the real partition publisher to retain the queue on rejection before 008. After installing additive 008, the same staged input must publish successfully, retain the numeric top-level value and preserve the separate nested value. Check both the full players array and saved individual response on exact JSON equality, including top-level zero, null and absent. Verify that a row inserted under 007 still omits the new field and that repeating 008 leaves explicit null unchanged. Sealed 003–007 remain unchanged. Use real disposable PostgreSQL and previously captured source only.

Suggested commit `fix: preserve match player positions in relational responses`.
