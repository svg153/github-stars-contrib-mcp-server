"""GraphQL queries and mutations for GitHub Stars API."""

# Contribution mutations
CREATE_CONTRIBUTIONS_MUTATION = """
    mutation CreateContributions($data: [ContributionInput!]!) {
        createContributions(data: $data) {
            id
            __typename
        }
    }
    """.strip()

CREATE_CONTRIBUTION_MUTATION = """
    mutation CreateContribution($data: ContributionInput!) {
        createContribution(data: $data) {
            id
            __typename
        }
    }
    """.strip()

UPDATE_CONTRIBUTION_MUTATION = """
    mutation UpdateContribution($id: String!, $data: ContributionInput!) {
        updateContribution(id: $id, data: $data) {
            id
            title
            __typename
        }
    }
    """.strip()

DELETE_CONTRIBUTION_MUTATION = """
    mutation DeleteContribution($id: String!) {
        deleteContribution(id: $id) {
            id
            __typename
        }
    }
    """.strip()

# Link mutations
CREATE_LINK_MUTATION = """
    mutation CreateLink($link: URL!, $platform: PlatformType!) {
        createLink(data: {link: $link, platform: $platform}) {
            id
            __typename
        }
    }
    """.strip()

UPDATE_LINK_MUTATION = """
    mutation UpdateLink($id: String!, $link: URL!, $platform: PlatformType!) {
        updateLink(id: $id, data: {link: $link, platform: $platform}) {
            id
            link
            __typename
        }
    }
    """.strip()

DELETE_LINK_MUTATION = """
    mutation DeleteLink($id: String!) {
        deleteLink(id: $id) {
            id
            __typename
        }
    }
    """.strip()

# Profile queries and mutations
USER_DATA_QUERY = """
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
    """.strip()

GET_STARS_QUERY = """
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
    """.strip()

USER_QUERY = """
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
    """.strip()

UPDATE_PROFILE_MUTATION = """
    mutation UpdateProfile($data: NomineeProfileInput!) {
        updateProfile(data: $data) {
            id
            __typename
        }
    }
    """.strip()
