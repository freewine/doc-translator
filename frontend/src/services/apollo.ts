import { ApolloClient, InMemoryCache, HttpLink, ApolloLink, CombinedGraphQLErrors } from '@apollo/client/core'
import { ErrorLink, onError } from '@apollo/client/link/error'

// HTTP link for GraphQL endpoint
const httpLink = new HttpLink({
  uri: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/graphql',
})

// Auth link to attach JWT token to requests
const authLink = new ApolloLink((operation, forward) => {
  const token = localStorage.getItem('auth_token')
  
  operation.setContext({
    headers: {
      authorization: token ? `Bearer ${token}` : '',
    },
  })
  
  return forward(operation)
})

// Error handling link for authentication errors
const errorLink: ErrorLink = onError(({ error }) => {
  // Check if it's a GraphQL error
  if (CombinedGraphQLErrors.is(error)) {
    error.errors.forEach((graphQLError) => {
      const { message, locations, path, extensions } = graphQLError
      console.error(
        `[GraphQL error]: Message: ${message}, Location: ${locations}, Path: ${path}`,
        extensions
      )
      
      // Handle authentication errors
      if (extensions?.code === 'UNAUTHENTICATED' || extensions?.code === 'UNAUTHORIZED') {
        localStorage.removeItem('auth_token')
        window.location.href = '/login'
      }
    })
  } else {
    // Network or other errors
    console.error(`[Network error]: ${error}`)
  }
})

// Create Apollo Client with link chain
export const apolloClient = new ApolloClient({
  link: ApolloLink.from([errorLink, authLink, httpLink]),
  cache: new InMemoryCache({
    typePolicies: {
      Query: {
        fields: {
          job: {
            read(existing, { args, toReference }) {
              return existing || toReference({ __typename: 'TranslationJob', id: args?.id })
            },
          },
        },
      },
    },
  }),
  defaultOptions: {
    watchQuery: {
      fetchPolicy: 'cache-and-network',
      errorPolicy: 'all',
    },
    query: {
      fetchPolicy: 'network-only',
      errorPolicy: 'all',
    },
    mutate: {
      errorPolicy: 'all',
    },
  },
})
