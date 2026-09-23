/*****************************************************************************
    created:    2002-02-12
    copyright:    2002, NCSoft. All Rights Reserved
    author(s):    Peter M. Freese
    
    purpose:    Includes the (non-standard) <hashmap> template class
*****************************************************************************/

#ifndef   INCLUDED_corStlHashmap
#define   INCLUDED_corStlHashmap
#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

#include "corStdPre_P.h"
#if CORE_COMPILER_GNU&!CORE_SYSTEM_PS3
#include <ext/unordered_map>
#elif CORE_SYSTEM_XENON
#include <unordered_map>
#else
#include <unordered_map>
#endif
#include "corStdPost_P.h"

#include "corStlHashTraits.h"

// The idea here is to define HashMap/HashMultiMap template classes
// that mask incompatibilities between VC.NET and GCC.

#if CORE_COMPILER_MSVC7 || CORE_COMPILER_MSVC8
#define        stdhash    stdext

template < typename KeyType,
           typename ValueType,
           class Traits = corHashTraits<KeyType> >
class HashMap : public std::unordered_map<KeyType, ValueType, corHashTraitsAux<Traits> > { };

template < typename KeyType,
           typename ValueType,
           class Traits = corHashTraits<KeyType> >
class HashMultiMap : public std::unordered_multimap<KeyType, ValueType, corHashTraitsAux<Traits> > { };


#elif CORE_COMPILER_MSVC || CORE_SYSTEM_PS3
#define        stdhash    std

template < typename KeyType,
typename ValueType,
class Traits = corHashTraits<KeyType> >
class HashMap : public std::unordered_map<KeyType, ValueType, corHashTraitsAux<Traits> > { };

template < typename KeyType,
typename ValueType,
class Traits = corHashTraits<KeyType> >
class HashMultiMap : public std::unordered_multimap<KeyType, ValueType, corHashTraitsAux<Traits> > { };


#elif CORE_COMPILER_GNU
#define        stdhash

template < typename KeyType,
           typename ValueType,
           class Traits = corHashTraits<KeyType> >
class HashMap : public std::unordered_map<KeyType, ValueType, corHashTraitsAux<Traits>, corHashTraitsAux<Traits> > { };

template < typename KeyType,
           typename ValueType,
           class Traits = corHashTraits<KeyType> >
class HashMultiMap : public std::unordered_multimap<KeyType, ValueType, corHashTraitsAux<Traits>, corHashTraitsAux<Traits> > { };

#else
# error "Unknown compiler."
#endif

#if CORE_COMPILER_GNU&!CORE_SYSTEM_PS3

// We also have to specialize insert_iterator, because GCC's hash_map
// doesn't have the supposedly standard 'insert(iter, value)' method.
// What a pain in the ass.

// Note: this is copied verbatim from stl_hash_map.h and modified
// using the 'search and replace' advanced programming technique.
// Don't worry if it looks ugly.  It makes shit work.

namespace std
{

template <class KeyType, class ValueType, class Traits>
class insert_iterator< HashMap<KeyType, ValueType, Traits> >
{
protected:
  typedef HashMap<KeyType, ValueType, Traits> _Container;
  _Container* container;
public:
  typedef _Container          container_type;
  typedef output_iterator_tag iterator_category;
  typedef void                value_type;
  typedef void                difference_type;
  typedef void                pointer;
  typedef void                reference;

  insert_iterator(_Container& __x) : container(&__x) {}
  insert_iterator(_Container& __x, typename _Container::iterator)
    : container(&__x) {}
  insert_iterator<_Container>&
  operator=(const typename _Container::value_type& __value) {
    container->insert(__value);
    return *this;
  }
  insert_iterator<_Container>& operator*() { return *this; }
  insert_iterator<_Container>& operator++() { return *this; }
  insert_iterator<_Container>& operator++(int) { return *this; }
};

template <class KeyType, class ValueType, class Traits>
class insert_iterator< HashMultiMap<KeyType, ValueType, Traits> >
{
protected:
  typedef HashMultiMap<KeyType, ValueType, Traits> _Container;
  _Container* container;
public:
  typedef _Container          container_type;
  typedef output_iterator_tag iterator_category;
  typedef void                value_type;
  typedef void                difference_type;
  typedef void                pointer;
  typedef void                reference;

  insert_iterator(_Container& __x) : container(&__x) {}
  insert_iterator(_Container& __x, typename _Container::iterator)
    : container(&__x) {}
  insert_iterator<_Container>&
  operator=(const typename _Container::value_type& __value) {
    container->insert(__value);
    return *this;
  }
  insert_iterator<_Container>& operator*() { return *this; }
  insert_iterator<_Container>& operator++() { return *this; }
  insert_iterator<_Container>& operator++(int) { return *this; }
};

} // namespace std

#endif // GCC

#endif // INCLUDED_corStlHashmap
