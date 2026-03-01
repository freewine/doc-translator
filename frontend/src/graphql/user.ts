import { gql } from '@apollo/client/core'

// User Queries
export const USERS_QUERY = gql`
  query Users($includeDeleted: Boolean) {
    users(includeDeleted: $includeDeleted) {
      username
      role
      status
      mustChangePassword
      failedLoginCount
      createdAt
      updatedAt
      deletedAt
    }
  }
`

export const USER_QUERY = gql`
  query User($username: String!) {
    user(username: $username) {
      username
      role
      status
      mustChangePassword
      failedLoginCount
      createdAt
      updatedAt
      deletedAt
    }
  }
`

// User Mutations
export const CREATE_USER_MUTATION = gql`
  mutation CreateUser($username: String!, $password: String!, $role: String!) {
    createUser(username: $username, password: $password, role: $role) {
      username
      role
      status
      mustChangePassword
      createdAt
    }
  }
`

export const UPDATE_USER_MUTATION = gql`
  mutation UpdateUser($username: String!, $password: String, $role: String) {
    updateUser(username: $username, password: $password, role: $role) {
      username
      role
      status
      updatedAt
    }
  }
`

export const DELETE_USER_MUTATION = gql`
  mutation DeleteUser($username: String!) {
    deleteUser(username: $username)
  }
`

export const UNLOCK_USER_MUTATION = gql`
  mutation UnlockUser($username: String!) {
    unlockUser(username: $username) {
      username
      status
    }
  }
`

export const CHANGE_PASSWORD_MUTATION = gql`
  mutation ChangeMyPassword($currentPassword: String!, $newPassword: String!) {
    changeMyPassword(currentPassword: $currentPassword, newPassword: $newPassword)
  }
`
