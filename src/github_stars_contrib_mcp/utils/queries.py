"""GraphQL queries and mutations for GitHub Stars API."""

# Contribution mutations
CREATE_CONTRIBUTIONS_MUTATION = (
    """
    mutation CreateContributions($data: [ContributionCreateInput!]!) {
        createContributions(data: $data) {
            id
            __typename
        }
    }
    """
    .strip()
)

CREATE_CONTRIBUTION_MUTATION = (
    """
    mutation CreateContribution($type: ContributionType!, $date: GraphQLDateTime!, $title: String!, $url: String!, $description: String!) {
        createContribution(data: {type: $type, date: $date, title: $title, url: $url, description: $description}) {
            id
            __typename
        }
    }
    """
    .strip()
)

UPDATE_CONTRIBUTION_MUTATION = (
    """
    mutation UpdateContribution($id: ID!, $data: ContributionUpdateInput!) {
        updateContribution(id: $id, data: $data) {
            id
            title
            __typename
        }
    }
    """
    .strip()
)

DELETE_CONTRIBUTION_MUTATION = (
    """
    mutation DeleteContribution($id: ID!) {
        deleteContribution(id: $id) {
            id
            __typename
        }
    }
    """
    .strip()
)

# Link mutations
CREATE_LINK_MUTATION = (
    """
    mutation CreateLink($link: String!, $platform: Platform!) {
        createLink(data: {link: $link, platform: $platform}) {
            id
            __typename
        }
    }
    """
    .strip()
)

UPDATE_LINK_MUTATION = (
    """
    mutation UpdateLink($id: ID!, $link: String!, $platform: Platform!) {
        updateLink(id: $id, data: {link: $link, platform: $platform}) {
            id
            __typename
        }
    }
    """
    .strip()
)

DELETE_LINK_MUTATION = (
    """
    mutation DeleteLink($id: ID!) {
        deleteLink(id: $id) {
            id
            __typename
        }
    }
    """
    .strip()
)

# Profile queries and mutations
USER_DATA_QUERY = (
    """
    query UserData {
        loggedUser {
            id
            username
            email
            nominee {
                status
                avatar
                name
                bio
                country
                birthdate
                reason
                jobTitle
                company
                phoneNumber
                address
                state
                city
                zipcode
                links {
                    id
                    link
                    platform
                    __typename
                }
                contributions {
                    id
                    type
                    date
                    title
                    url
                    description
                    __typename
                }
                __typename
            }
            __typename
        }
    }
    """
    .strip()
)

GET_STARS_QUERY = (
    """
    query GetStars($username: String!) {
        publicProfile(username: $username) {
            username
            contributions {
                id
                type
                date
                title
                url
                description
                __typename
            }
            __typename
        }
    }
    """
    .strip()
)

USER_QUERY = (
    """
    query User {
        loggedUser {
            id
            username
            email
            nominee {
                status
                avatar
                name
                bio
                country
                birthdate
                reason
                jobTitle
                company
                phoneNumber
                address
                state
                city
                zipcode
                links {
                    id
                    link
                    platform
                    __typename
                }
                contributions {
                    id
                    type
                    date
                    title
                    url
                    description
                    __typename
                }
                __typename
            }
            __typename
        }
    }
    """
    .strip()
)

UPDATE_PROFILE_MUTATION = (
    """
    mutation UpdateProfile($data: ProfileUpdateInput) {
        updateProfile(data: $data) {
            id
            __typename
        }
    }
    """
    .strip()
)