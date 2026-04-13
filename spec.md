The end state is a repository of human-validated BMRs that are the result of human review of the BMRs (decision matrix), with HTML reporting mechanism 
(i)Humans generate records with handwriting
(ii) Model parses and formats handwriting to schema (JSON, pydantic etc) for extraction, judges /scores extracted value as (0,1) extraction
(iii) LLM as judge results are presented to a user in a web app / HTML with final review from human - do entries look correct? can user update these values?
