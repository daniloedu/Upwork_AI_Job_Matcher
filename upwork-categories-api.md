# Upwork API Documentation: Categories and Ontology

## `ontologyCategories`

### Description
Fetch all enabled categories/subcategories/services

### Response
Returns `[OntologyCategory!]!`

### Example

**QUERY**
```graphql
query ontologyCategories {
  ontologyCategories {
    id
    preferredLabel
    altLabel
    slug
    ontologyId
    subcategories {
      ...OntologySubcategoryFragment
    }
    services {
      ...OntologyServiceFragment
    }
  }
}
```

**RESPONSE**
```json
{
  "data": {
    "ontologyCategories": [
      {
        "id": "4",
        "preferredLabel": "xyz789",
        "altLabel": ["abc123"],
        "slug": "abc123",
        "ontologyId": "abc123",
        "subcategories": [OntologySubcategory],
        "services": [OntologyService]
      }
    ]
  }
}
```

## `ontologyCategorySubcategory`

### Description
Return: list of category-subcategory pairs occupations for the occupation with the uid sent in the parameter

### Response
Returns `[CategorySubcategory!]!`

### Arguments
| Name | Description |
|------|-------------|
| `id` | `ID!` |

### Example

**QUERY**
```graphql
query ontologyCategorySubcategory($id: ID!) {
  ontologyCategorySubcategory(id: $id) {
    category {
      ...OccupationFragment
    }
    subcategory {
      ...OccupationFragment
    }
  }
}
```

**VARIABLES**
```json
{"id": 4}
```

**RESPONSE**
```json
{
  "data": {
    "ontologyCategorySubcategory": [
      {
        "category": Occupation,
        "subcategory": Occupation
      }
    ]
  }
}
```

## `ontologyOccupationsCategoriesServices`

### Description
Searches occupations categories services by list of category Uids.
Return: list of categories and a map of every category and related services

### Response
Returns a `CategoryServicesResponse`

### Arguments
| Name | Description |
|------|-------------|
| `categoryUids` | `[ID!]` |

### Example

**QUERY**
```graphql
query ontologyOccupationsCategoriesServices($categoryUids: [ID!]) {
  ontologyOccupationsCategoriesServices(categoryUids: $categoryUids) {
    categories {
      ...OccupationFragment
    }
    categoryServices {
      ...StringMapOccupationFragment
    }
  }
}
```

**VARIABLES**
```json
{"categoryUids": ["4"]}
```

**RESPONSE**
```json
{
  "data": {
    "ontologyOccupationsCategoriesServices": {
      "categories": [Occupation],
      "categoryServices": [StringMapOccupation]
    }
  }
}
```

## `ontologyOccupationsCategoriesServicesGraph`

### Description
Return a list of graph category services occupations for the occupation list with the uids sent in the parameter

### Response
Returns `[OntologyGraphNode!]`

### Arguments
| Name | Description |
|------|-------------|
| `categoryIds` | `[ID!]!` |

### Example

**QUERY**
```graphql
query ontologyOccupationsCategoriesServicesGraph($categoryIds: [ID!]!) {
  ontologyOccupationsCategoriesServicesGraph(categoryIds: $categoryIds) {
    id
    uid
    label
    types
    status
    properties {
      ...PropertyStringMapFragment
    }
    relationships {
      ...StringListMapFragment
    }
    metadata {
      ...StringMapElementFragment
    }
  }
}
```

**VARIABLES**
```json
{"categoryIds": [4]}
```

**RESPONSE**
```json
{
  "data": {
    "ontologyOccupationsCategoriesServicesGraph": [
      {
        "id": 4,
        "uid": "4",
        "label": "xyz789",
        "types": ["abc123"],
        "status": "ACTIVE",
        "properties": [PropertyStringMap],
        "relationships": [StringListMap],
        "metadata": [StringMapElement]
      }
    ]
  }
}
```

## `ontologyOccupationsCategoriesSubcategoriesGraph`

### Description
Return a list of graph category subcategories occupations

### Response
Returns `[OntologyGraphNode!]!`

### Example

**QUERY**
```graphql
query ontologyOccupationsCategoriesSubcategoriesGraph {
  ontologyOccupationsCategoriesSubcategoriesGraph {
    id
    uid
    label
    types
    status
    properties {
      ...PropertyStringMapFragment
    }
    relationships {
      ...StringListMapFragment
    }
    metadata {
      ...StringMapElementFragment
    }
  }
}
```

**RESPONSE**
```json
{
  "data": {
    "ontologyOccupationsCategoriesSubcategoriesGraph": [
      {
        "id": "4",
        "uid": "4",
        "label": "abc123",
        "types": ["abc123"],
        "status": "ACTIVE",
        "properties": [PropertyStringMap],
        "relationships": [StringListMap],
        "metadata": [StringMapElement]
      }
    ]
  }
}
```

## `ontologyOccupationServices`

### Description
Return: list of services for a specific occupation

### Response
Returns `[Occupation!]!`

### Arguments
| Name | Description |
|------|-------------|
| `id` | `ID!` |

### Example

**QUERY**
```graphql
query ontologyOccupationServices($id: ID!) {
  ontologyOccupationServices(id: $id) {
    id
    ontologyId
    type
    entityStatus
    preferredLabel
    definition
    createdDateTime
    modifiedDateTime
    skills {
      ...SkillFragment
    }
  }
}
```

**VARIABLES**
```json
{"id": "4"}
```

**RESPONSE**
```json
{
  "data": {
    "ontologyOccupationServices": [
      {
        "id": "4",
        "ontologyId": "xyz789",
        "type": ["OCCUPATION"],
        "entityStatus": "ACTIVE",
        "preferredLabel": "abc123",
        "definition": "abc123",
        "createdDateTime": "xyz789",
        "modifiedDateTime": "abc123",
        "skills": [Skill]
      }
    ]
  }
}
```

## `ontologyOccupationSkillsCount`

### Description
Return: number of active attributes with type Skill available in the occupation

### Response
Returns an `Int!`

### Arguments
| Name | Description |
|------|-------------|
| `id` | `ID!` |

### Example

**QUERY**
```graphql
query ontologyOccupationSkillsCount($id: ID!) {
  ontologyOccupationSkillsCount(id: $id)
}
```

**VARIABLES**
```json
{"id": "4"}
```

**RESPONSE**
```json
{"data": {"ontologyOccupationSkillsCount": 123}}
```
