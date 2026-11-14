-- Q2: How old is the installed base? Age distribution in brackets (reference date 2026-11-01).
SELECT CASE WHEN age_years < 5 THEN '1: under 5 years'
            WHEN age_years < 10 THEN '2: 5-9 years'
            WHEN age_years < 15 THEN '3: 10-14 years'
            ELSE '4: 15+ years' END AS age_bracket,
       COUNT(*) AS machines
FROM (SELECT (julianday('2026-11-01') - julianday(install_date)) / 365.25 AS age_years
      FROM clean_machines)
GROUP BY age_bracket
ORDER BY age_bracket;
