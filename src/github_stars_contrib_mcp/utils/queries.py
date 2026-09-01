"""GraphQL queries and mutations for Stars surfaces without a REST replacement."""

# Contribution create/update/delete mutations were removed on 2026-09-01.
# Contributions are handled by StarsClient through the REST API instead.

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

# Authenticated profile and public-profile reads remain on GraphQL because the
# announced Contributions migration does not document REST replacements for
# these profile/link surfaces.
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
