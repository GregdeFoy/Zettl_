-- SQL queries to identify and remove duplicate notes from Zettl database
-- Keeps the oldest note (by created_at) when duplicates are found

-- 1. First, let's identify duplicates to see what we're dealing with
-- This query shows all duplicate content groups
WITH duplicate_groups AS (
    SELECT
        content,
        COUNT(*) as copy_count,
        MIN(created_at) as oldest_created,
        array_agg(id ORDER BY created_at) as all_ids,
        array_agg(id ORDER BY created_at)[1] as keep_id,
        array_agg(id ORDER BY created_at)[2:] as delete_ids
    FROM notes
    GROUP BY content
    HAVING COUNT(*) > 1
)
SELECT
    LEFT(content, 100) as content_preview,
    copy_count,
    keep_id as note_to_keep,
    delete_ids as notes_to_delete,
    oldest_created
FROM duplicate_groups
ORDER BY copy_count DESC, oldest_created;

-- 2. Count how many duplicates we have
SELECT
    COUNT(DISTINCT content) as duplicate_groups,
    SUM(COUNT(*)) as total_duplicate_notes,
    SUM(COUNT(*) - 1) as notes_to_delete
FROM notes
GROUP BY content
HAVING COUNT(*) > 1;

-- 3. DELETE DUPLICATES (keeping the oldest one of each group)
-- BE CAREFUL: This will permanently delete notes!
-- Uncomment and run only after reviewing the results above
/*
DELETE FROM notes
WHERE id IN (
    SELECT id
    FROM (
        SELECT id,
               content,
               created_at,
               ROW_NUMBER() OVER (PARTITION BY content ORDER BY created_at) as rn
        FROM notes
    ) duplicates
    WHERE rn > 1
);
*/

-- Alternative: Delete duplicates with a more explicit approach
-- This shows exactly what will be deleted
/*
WITH duplicates_to_delete AS (
    SELECT id
    FROM (
        SELECT
            id,
            content,
            created_at,
            ROW_NUMBER() OVER (PARTITION BY content ORDER BY created_at) as rn
        FROM notes
    ) ranked_notes
    WHERE rn > 1
)
DELETE FROM notes
WHERE id IN (SELECT id FROM duplicates_to_delete)
RETURNING id, LEFT(content, 100) as deleted_content;
*/