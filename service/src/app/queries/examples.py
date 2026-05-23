def select_units_with_all_children_text():
    """
    Serves as an example for querying persons and organisational units relationship

    Example usage:
    ```
    df = polars.read_database(
        sqlalchemy.sql.text(select_units_with_all_children_text()),
        conn,
    )
    ```
    """
    return """
    with recursive units_parents as (
        select
            ou.organisational_unit_id,
            uuid(parent_text) as parent
        from organisational_units ou
        left outer join lateral jsonb_array_elements_text(
            case jsonb_typeof(ou.parents)
                when 'array' then ou.parents
                else '[]' end
       ) as parent_text on true
    ),
    units_parents_filtered_start as (
        select up.*
        from units_parents up
        join organisational_units ou
        on up.organisational_unit_id = ou.organisational_unit_id
        where ou.type_id = 17278
    ),
    united_recursively AS (
        select
            up.organisational_unit_id,
            up.organisational_unit_id as highest_parent,
            1 as level
            from units_parents_filtered_start up
        UNION all
        select
            up.organisational_unit_id,
            u.highest_parent,
            u.level + 1 as level
        from units_parents up
        inner join united_recursively u
        on up.parent = u.organisational_unit_id
    )
    select * from united_recursively
    order by level, highest_parent, organisational_unit_id;
    """
